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
import requests
import requests.exceptions
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

# Load configurations and localization
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

# Initial config load
load_config("locale/en-US.lang")

# Log configuration
debug = bool(os.environ.get('debug', False))
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG if debug else logging.INFO)

# Thread pool max workers
executor = ThreadPoolExecutor(max_workers=5)

# Globals for conversation
previous_response_id = None
last_interaction_date = None
is_apl_supported = False
user_locale = "US"
apl_document_token = str(uuid.uuid4())

# OpenClaw configuration
openclaw_url = os.environ.get('openclaw_url', "").strip("/")
openclaw_api_key = os.environ.get('openclaw_api_key', None)
openclaw_model = os.environ.get('openclaw_model', None)
openclaw_system_prompt = os.environ.get('openclaw_system_prompt', None)

# Feature flags
ask_for_further_commands = str(os.environ.get('ask_for_further_commands', 'False')).lower()
suppress_greeting = str(os.environ.get('suppress_greeting', 'False')).lower()
enable_acknowledgment_sound = str(os.environ.get('enable_acknowledgment_sound', 'False')).lower()


def localize(handler_input):
    locale = handler_input.request_envelope.request.locale
    load_config(f"locale/{locale}.lang")
    global user_locale
    user_locale = locale.split("-")[1]


class LaunchRequestHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return ask_utils.is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input):
        global previous_response_id, last_interaction_date, is_apl_supported

        localize(handler_input)

        # Validate required configuration
        if not openclaw_url or not openclaw_api_key:
            logger.error("Missing 'openclaw_url' or 'openclaw_api_key' environment variables.")
            speak_output = globals().get("alexa_speak_error")
            return handler_input.response_builder.speak(speak_output).response

        # Reset conversation state for new session
        previous_response_id = None

        # Check for screen support
        device = handler_input.request_envelope.context.system.device
        is_apl_supported = device.supported_interfaces.alexa_presentation_apl is not None
        logger.debug("Device: " + repr(device))

        if is_apl_supported:
            handler_input.response_builder.add_directive(
                RenderDocumentDirective(token=apl_document_token, document=load_template("apl_welcome.json"))
            )

        # Welcome greeting logic
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


# Helper function to send progressive response with acknowledgment sound
def send_acknowledgment_sound(handler_input, request):
    """
    Sends a progressive response with an acknowledgment sound to inform the user
    that their request is being processed. This bypasses Alexa's 8-second timeout.

    Args:
        handler_input: The handler input from Alexa
        request: The request object containing request_id

    Returns:
        bool: True if sound was sent successfully, False otherwise
    """
    if not request.request_id:
        logger.warning("Cannot send acknowledgment sound: missing request_id")
        return False

    processing_msg = globals().get("alexa_speak_processing")
    if not processing_msg:
        logger.warning("Cannot send acknowledgment sound: missing alexa_speak_processing")
        return False

    try:
        directive_header = Header(request_id=request.request_id)
        speak_directive = SpeakDirective(speech=processing_msg)
        directive_request = SendDirectiveRequest(
            header=directive_header, directive=speak_directive
        )
        directive_service_client = handler_input.service_client_factory.get_directive_service()
        directive_service_client.enqueue(directive_request)
        logger.debug("Acknowledgment sound sent via progressive response")
        return True
    except Exception as e:
        logger.warning(f"Failed to send acknowledgment sound: {e}")
        return False


# Execute the asynchronous part with asyncio
def run_async_in_executor(func, *args):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(loop.run_in_executor(executor, func, *args))
    finally:
        loop.close()


class GptQueryIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("GptQueryIntent")(handler_input)

    def handle(self, handler_input):
        localize(handler_input)

        request = handler_input.request_envelope.request
        response_builder = handler_input.response_builder

        # Extract user query
        query = request.intent.slots["query"].value
        logger.info(f"Query received from Alexa: {query}")

        # Handle keyword-based logic
        keyword_response = keywords_exec(query, handler_input)
        if keyword_response:
            return keyword_response

        # Send acknowledgment sound if enabled (using progressive response)
        if enable_acknowledgment_sound == "true":
            send_acknowledgment_sound(handler_input, request)

        # Run async call
        response = run_async_in_executor(process_conversation, query)

        logger.debug(f"Ask for further commands enabled: {ask_for_further_commands}")
        if ask_for_further_commands == "true":
            return response_builder.speak(response).ask(globals().get("alexa_speak_question")).response
        else:
            return response_builder.speak(response).set_should_end_session(True).response


# Handles keywords to execute specific commands
def keywords_exec(query, handler_input):
    # Commands to close the skill — only if query has 3 or fewer words and matches closing keywords exactly
    keywords_close_skill = [k.strip().lower() for k in globals().get("keywords_to_close_skill").split(";")]
    query_words = query.lower().split()
    if len(query_words) <= 3:
        for kc in keywords_close_skill:
            if re.search(r'\b' + re.escape(kc) + r'\b', query.lower()):
                logger.info("Closing skill from keyword command")
                return CancelOrStopIntentHandler().handle(handler_input)
    return None


# Calls the OpenClaw API using the OpenAI Responses API
def process_conversation(query):
    global previous_response_id

    if not openclaw_url:
        logger.error("Please set 'openclaw_url' AWS Lambda environment variable.")
        return globals().get("alexa_speak_error")

    if not openclaw_api_key:
        logger.error("Please set 'openclaw_api_key' AWS Lambda environment variable.")
        return globals().get("alexa_speak_error")

    try:
        headers = {
            "Authorization": "Bearer {}".format(openclaw_api_key),
            "Content-Type": "application/json",
        }
        data = {
            "input": replace_words(query),
        }
        if openclaw_model:
            data["model"] = openclaw_model
        if openclaw_system_prompt:
            data["instructions"] = openclaw_system_prompt
        if previous_response_id:
            data["previous_response_id"] = previous_response_id

        api_url = "{}/v1/responses".format(openclaw_url)
        logger.debug(f"OpenClaw request url: {api_url}")
        logger.debug(f"OpenClaw request data: {data}")

        response = requests.post(api_url, headers=headers, json=data, timeout=25)

        logger.debug(f"OpenClaw response status: {response.status_code}")
        logger.debug(f"OpenClaw response data: {response.text}")

        if response.status_code == 200:
            response_data = response.json()
            output = response_data.get("output", [])
            content = ""
            if output:
                content_blocks = output[0].get("content", [])
                if content_blocks:
                    content = content_blocks[0].get("text", "")

            if not content:
                logger.error(f"Empty content in response: {response_data}")
                return globals().get("alexa_speak_error")

            previous_response_id = response_data.get("id", previous_response_id)
            return improve_response(content)
        else:
            logger.error(f"HTTP error {response.status_code}: {response.text}")
            return globals().get("alexa_speak_error")

    except requests.exceptions.Timeout as te:
        logger.error(f"Timeout when communicating with OpenClaw: {str(te)}", exc_info=True)
        return globals().get("alexa_speak_timeout")

    except Exception as e:
        logger.error(f"Error processing response: {str(e)}", exc_info=True)
        return globals().get("alexa_speak_error")


# Replaces incorrectly generated words by Alexa interpreter in the query
def replace_words(query):
    query = query.replace('4.º', 'quarto')
    return query


# Replaces words and special characters to improve API response speech
def improve_response(speech):
    global user_locale
    speech = speech.replace(':\n\n', '').replace('\n\n', '. ').replace('\n', ',').replace('-', '').replace('_', ' ')

    if user_locale == "DE":
        speech = re.sub(r'(\d+)\.(\d{1,3})(?!\d)', r'\1,\2', speech)

    speech = re.sub(r'[^A-Za-z0-9çÇáàâãäéèêíïóôõöúüñÁÀÂÃÄÉÈÊÍÏÓÔÕÖÚÜÑ\sß.,!?°]', '', speech)
    return speech


# Loads the APL screen template
def load_template(filepath):
    with open(filepath, encoding='utf-8') as f:
        template = json.load(f)

    if filepath == 'apl_welcome.json':
        template['mainTemplate']['items'][0]['items'][2]['text'] = globals().get("echo_screen_welcome_text")
        template['mainTemplate']['items'][0]['items'][3]['text'] = globals().get("echo_screen_click_text")

    return template


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


class SessionEndedRequestHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return ask_utils.is_request_type("SessionEndedRequest")(handler_input)

    def handle(self, handler_input):
        return handler_input.response_builder.response


class CanFulfillIntentRequestHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return ask_utils.is_request_type("CanFulfillIntentRequest")(handler_input)

    def handle(self, handler_input):
        localize(handler_input)
        intent_name = handler_input.request_envelope.request.intent.name if handler_input.request_envelope.request.intent else None
        if intent_name == "GptQueryIntent":
            return handler_input.response_builder.can_fulfill("YES").add_can_fulfill_intent("YES").response
        else:
            return handler_input.response_builder.can_fulfill("NO").add_can_fulfill_intent("NO").response


class CatchAllExceptionHandler(AbstractExceptionHandler):
    def can_handle(self, handler_input, exception):
        return True

    def handle(self, handler_input, exception):
        logger.error(exception, exc_info=True)
        speak_output = globals().get("alexa_speak_error")
        return handler_input.response_builder.speak(speak_output).ask(speak_output).response


sb = CustomSkillBuilder(api_client=DefaultApiClient())
sb.add_request_handler(LaunchRequestHandler())
sb.add_request_handler(GptQueryIntentHandler())
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(CancelOrStopIntentHandler())
sb.add_request_handler(SessionEndedRequestHandler())
sb.add_request_handler(CanFulfillIntentRequestHandler())
sb.add_exception_handler(CatchAllExceptionHandler())
lambda_handler = sb.lambda_handler()
