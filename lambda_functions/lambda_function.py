# -*- coding: utf-8 -*-
import warnings
import sys

if not sys.warnoptions:
    warnings.filterwarnings("ignore", category=SyntaxWarning)

import os
import re
import logging
import json
import random
import asyncio
import uuid
import socket
import urllib.request
import urllib.error

import ask_sdk_core.utils as ask_utils

from ask_sdk_core.skill_builder import CustomSkillBuilder
from ask_sdk_core.api_client import DefaultApiClient
from ask_sdk_core.dispatch_components import AbstractRequestHandler, AbstractExceptionHandler
from ask_sdk_model.interfaces.alexa.presentation.apl import RenderDocumentDirective
from ask_sdk_model.services.directive import (
    SendDirectiveRequest, Header, SpeakDirective
)
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor


# --------------------------------------------------
# Logging
# --------------------------------------------------

debug = bool(os.environ.get('debug', False))
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG if debug else logging.INFO)


# --------------------------------------------------
# Config + Globals
# --------------------------------------------------

executor = ThreadPoolExecutor(max_workers=5)

previous_response_id = None
last_interaction_date = None
is_apl_supported = False
user_locale = "US"
apl_document_token = str(uuid.uuid4())

openclaw_url = os.environ.get('openclaw_url', "").strip("/")
openclaw_api_key = os.environ.get('openclaw_api_key', None)
openclaw_model = os.environ.get('openclaw_model', None)

ask_for_further_commands = str(os.environ.get('ask_for_further_commands', 'False')).lower()
suppress_greeting = str(os.environ.get('suppress_greeting', 'False')).lower()
enable_acknowledgment_sound = str(os.environ.get('enable_acknowledgment_sound', 'False')).lower()


# --------------------------------------------------
# Localization Loader
# --------------------------------------------------

def load_config(file_name):
    if str(file_name).endswith(".lang") and not os.path.exists(file_name):
        file_name = "locale/en-US.lang"
    try:
        with open(file_name, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or '=' not in line:
                    continue
                name, value = line.split('=', 1)
                globals()[name] = value
    except Exception as e:
        logger.error(f"Error loading file: {str(e)}")


load_config("locale/en-US.lang")


def localize(handler_input):
    locale = handler_input.request_envelope.request.locale
    load_config(f"locale/{locale}.lang")
    global user_locale
    user_locale = locale.split("-")[1]


# --------------------------------------------------
# Launch Handler
# --------------------------------------------------

class LaunchRequestHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return ask_utils.is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input):
        global previous_response_id, last_interaction_date, is_apl_supported

        localize(handler_input)

        if not openclaw_url or not openclaw_api_key:
            speak_output = globals().get("alexa_speak_error")
            return handler_input.response_builder.speak(speak_output).response

        previous_response_id = None

        device = handler_input.request_envelope.context.system.device
        is_apl_supported = device.supported_interfaces.alexa_presentation_apl is not None

        now = datetime.now(timezone(timedelta(hours=-3)))
        current_date = now.strftime('%Y-%m-%d')

        speak_output = globals().get("alexa_speak_next_message")
        if last_interaction_date != current_date:
            speak_output = globals().get("alexa_speak_welcome_message")
            last_interaction_date = current_date

        if suppress_greeting == "true":
            return handler_input.response_builder.ask("").response
        else:
            return handler_input.response_builder.speak(speak_output).ask(speak_output).response


# --------------------------------------------------
# Progressive Response
# --------------------------------------------------

def send_acknowledgment_sound(handler_input, request):
    if not request.request_id:
        return False

    raw = globals().get("alexa_speak_processing", "")
    parts = [p.strip() for p in raw.split(";") if p.strip()]
    processing_msg = random.choice(parts) if parts else ""
    if not processing_msg:
        return False

    try:
        directive_header = Header(request_id=request.request_id)
        speak_directive = SpeakDirective(speech=processing_msg)
        directive_request = SendDirectiveRequest(
            header=directive_header, directive=speak_directive
        )
        directive_service_client = handler_input.service_client_factory.get_directive_service()
        directive_service_client.enqueue(directive_request)
        return True
    except Exception:
        return False


def run_async_in_executor(func, *args):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(loop.run_in_executor(executor, func, *args))
    finally:
        loop.close()


# --------------------------------------------------
# GPT Intent Handler
# --------------------------------------------------

class GptQueryIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("GptQueryIntent")(handler_input)

    def handle(self, handler_input):
        localize(handler_input)

        request = handler_input.request_envelope.request
        response_builder = handler_input.response_builder

        query = request.intent.slots["query"].value
        logger.info(f"Query received from Alexa: {query}")

        if enable_acknowledgment_sound == "true":
            send_acknowledgment_sound(handler_input, request)

        response = run_async_in_executor(process_conversation, query)

        if ask_for_further_commands == "true":
            return response_builder.speak(response).ask(globals().get("alexa_speak_question")).response
        else:
            return response_builder.speak(response).set_should_end_session(True).response


# --------------------------------------------------
# OpenClaw Communication (no requests)
# --------------------------------------------------

def _http_post_json(url: str, headers: dict, payload: dict, timeout_seconds: int = 20) -> tuple[int, str]:
    """
    Minimal JSON POST using Python stdlib (dependency-free).
    Returns: (status_code, response_text)
    """
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url=url,
        data=body,
        headers=headers,
        method="POST",
    )

    # Ensure timeout applies to connect+read in urllib
    with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
        status = getattr(resp, "status", 200)  # status exists in py3
        text = resp.read().decode("utf-8", errors="replace")
        return status, text


def process_conversation(query):
    global previous_response_id

    if not openclaw_url or not openclaw_api_key:
        return globals().get("alexa_speak_error")

    try:
        headers = {
            "Authorization": f"Bearer {openclaw_api_key}",
            "Content-Type": "application/json",
        }

        data = {"input": query}
        if openclaw_model:
            data["model"] = openclaw_model

        status_code, response_text = _http_post_json(
            f"{openclaw_url}/v1/responses",
            headers=headers,
            payload=data,
            timeout_seconds=20
        )

        if status_code != 200:
            logger.error(f"HTTP error {status_code}: {response_text}")
            return globals().get("alexa_speak_error")

        try:
            response_data = json.loads(response_text)
        except Exception:
            logger.error(f"Invalid JSON response: {response_text[:1000]}")
            return globals().get("alexa_speak_error")

        content = ""

        # Chat Completion format
        if "choices" in response_data:
            choices = response_data.get("choices", [])
            if choices:
                content = choices[0].get("message", {}).get("content", "")

        # Fallback for Responses API format
        elif "output" in response_data:
            for item in response_data.get("output", []):
                for block in item.get("content", []):
                    if block.get("type") == "output_text":
                        content += block.get("text", "")

        if not content.strip():
            logger.error(f"Empty content in response: {response_data}")
            return globals().get("alexa_speak_error")

        previous_response_id = response_data.get("id", previous_response_id)

        return improve_response(content)

    except (socket.timeout, TimeoutError):
        logger.error("Timeout communicating with OpenClaw")
        return globals().get("alexa_speak_timeout")

    except urllib.error.HTTPError as e:
        # HTTPError is also a file-like response; read body for logs
        body = ""
        try:
            body = e.read().decode("utf-8", errors="replace")
        except Exception:
            pass
        logger.error(f"HTTP error {e.code}: {body}")
        return globals().get("alexa_speak_error")

    except urllib.error.URLError as e:
        logger.error(f"Network error communicating with OpenClaw: {e}")
        return globals().get("alexa_speak_timeout")

    except Exception as e:
        logger.error(f"Processing error: {str(e)}")
        return globals().get("alexa_speak_error")


# --------------------------------------------------
# Response Cleanup
# --------------------------------------------------

def improve_response(speech):
    global user_locale
    speech = speech.replace('\n\n', '. ').replace('\n', ',').replace('_', ' ')
    if user_locale == "DE":
        speech = re.sub(r'(\d+)\.(\d{1,3})(?!\d)', r'\1,\2', speech)
    return speech


# --------------------------------------------------
# Other Handlers
# --------------------------------------------------

class HelpIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("AMAZON.HelpIntent")(handler_input)

    def handle(self, handler_input):
        speak_output = globals().get("alexa_speak_help")
        return handler_input.response_builder.speak(speak_output).ask(speak_output).response


class CancelOrStopIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("AMAZON.CancelIntent")(handler_input) or ask_utils.is_intent_name("AMAZON.StopIntent")(handler_input)

    def handle(self, handler_input):
        speak_output = random.choice(globals().get("alexa_speak_exit").split(";"))
        return handler_input.response_builder.speak(speak_output).set_should_end_session(True).response


class CatchAllExceptionHandler(AbstractExceptionHandler):
    def can_handle(self, handler_input, exception):
        return True

    def handle(self, handler_input, exception):
        logger.error(exception, exc_info=True)
        speak_output = globals().get("alexa_speak_error")
        return handler_input.response_builder.speak(speak_output).response


# --------------------------------------------------
# Skill Builder
# --------------------------------------------------

sb = CustomSkillBuilder(api_client=DefaultApiClient())
sb.add_request_handler(LaunchRequestHandler())
sb.add_request_handler(GptQueryIntentHandler())
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(CancelOrStopIntentHandler())
sb.add_exception_handler(CatchAllExceptionHandler())

lambda_handler = sb.lambda_handler()
