# INSTALLATION

## Table of Contents
1. [Requirements](#requirements)
2. [Create an Amazon Alexa Skill](#create-an-amazon-alexa-skill)
3. [Create an AWS Lambda Function](#create-an-aws-lambda-function)
4. [Add Code to the Lambda Function](#add-code-to-the-lambda-function)
5. [Configure Environment Variables](#configure-environment-variables)
6. [Test the Lambda Function](#test-the-lambda-function)
7. [Configure the Skill Service Endpoint](#configure-the-skill-service-endpoint)
8. [Enabling the Skill on the Alexa App](#enabling-the-skill-on-the-alexa-app)
9. [Alexa Locale](#alexa-locale)

---

## Requirements
- An OpenAI-compatible API endpoint accessible over HTTPS (e.g. `https://alexa.fluxato.com`). The endpoint must implement `POST /v1/chat/completions`.
- A Bearer API key for that endpoint.
- An Amazon Developer Account. Sign up [here](https://developer.amazon.com/).
- An Amazon Web Services (AWS) account to host the Lambda function. AWS Lambda is free for up to 1 million requests and 1 GB outbound data per month.

## Create an Amazon Alexa Skill
- Sign into the [Alexa Developer Console](https://developer.amazon.com/alexa/console/ask).
_Note: This must be created with the same `Amazon account` you use on your Alexa devices and app._
- Go to the `Alexa Skills` page and click `Create Skill`.
- In the `Name, Locale` step: input a skill name, select your default language, and click `Next`. _**Important**: The language of your skill must match your Amazon/Alexa account language. [More information about supported languages here](../../README.md#supported-languages)_
- In the `Experience, Model, Hosting service` step: select `Other` > `Custom` > `Provision your own`, then click `Next`.
- In the `Template` step: select `Start from Scratch` and click `Next`.
- Review and click `Create Skill`.

  ![](images/skill_review.png)
- In the next screen, in the right panel `Building your skill`:

  ![](images/skill_build.png)

  - Click `Invocation Name >`, set the invocation name (e.g. `alexa claw`), then click `Save`.
  - In the left navigation, go to `CUSTOM` > `Interaction Model` > `JSON Editor`, drag and drop the [`interactionModels.json` file](../interactionModels.json), then click `Save`.

  ![](images/skill_intmodel.png)

  - Still in the left navigation, go to `CUSTOM` > `Interfaces`, scroll down to `Alexa Presentation Language`, enable it, and uncheck `Hub Round` _(not compatible with this skill)_.

  ![](images/skill_interfaces.png)

  - Go to `CUSTOM` > `Endpoint` and note down `Your Skill ID`.
- Keep the `Alexa Developer Console` open — you will need it in a later step.

## Create an AWS Lambda Function
The Lambda function receives requests from Alexa and forwards them to your OpenAI-compatible endpoint.

Sign into your [AWS console](https://aws.amazon.com/console/).

## Add Code to the Lambda Function
- In the AWS console, navigate to `Lambda` under `Compute`.
- **IMPORTANT** — Alexa Skills are only supported in certain AWS regions. Select the one closest to your location:
  - **US East (N. Virginia)** for `English (US)`, `English (CA)`, `Portuguese (BR)` skills.
  - **EU (Ireland)** for `English (UK)`, `Italian`, `German (DE)`, `Spanish (ES)`, `French (FR)` skills.
  - **US West (Oregon)** for `Japanese` and `English (AU)` skills.
- Click `Functions` > `Create function`:
  - Select `Author from scratch`, enter a function name (e.g. `AlexaClaw`).
  - Select **Python 3.12** as the Runtime and **x86_64** architecture.
  - Leave the default execution role unchanged.
- Click `Create function`.

  ![](images/lambda_function.png)

- Expand `Function overview`, click `+ Add trigger`, select `Alexa` > `Alexa Skills Kit`, enter the `Skill ID` from the previous step, then click `Add`.

  ![](images/lambda_trigger.png)

- Scroll down to the `Code` tab > `Code source`, click `Upload from` > `zip file`.
- Download the latest release zip from the [Releases page](https://github.com/your-org/AlexaClaw/releases), upload it, and click `Save`.

  ![](images/lambda_code.png)

## Configure Environment Variables

In the Lambda function console, go to `Configuration` > `Environment variables` and add the following:

### Required

| Variable | Description | Example |
|---|---|---|
| `openclaw_url` | Base URL of your OpenAI-compatible endpoint (no trailing slash) | `https://alexa.fluxato.com` |
| `openclaw_api_key` | Bearer API key for authentication | `sk-...` |

### Optional

| Variable | Default | Description |
|---|---|---|
| `openclaw_model` | _(none)_ | Model name to pass in the request body (e.g. `gpt-4o`) |
| `openclaw_system_prompt` | _(none)_ | System prompt prepended to every conversation |
| `ask_for_further_commands` | `False` | When `true`, keeps the session open and asks "Anything else?" after each response |
| `suppress_greeting` | `False` | When `true`, skips the welcome phrase when the skill opens |
| `enable_acknowledgment_sound` | `False` | When `true`, plays "One moment please" immediately while waiting for the AI response — **recommended for slow models** |
| `debug` | `False` | When `true`, enables verbose debug logging in CloudWatch |

### How the API call works

The skill sends a `POST` request to `{openclaw_url}/v1/responses` using the OpenAI Responses API format:

```json
{
  "model": "your-model-name",
  "input": "What the user said",
  "instructions": "Your system prompt (optional)",
  "previous_response_id": "resp_abc123 (omitted on first turn)"
}
```

The skill expects an OpenAI Responses API-compatible response:

```json
{
  "id": "resp_xyz456",
  "output": [
    {
      "type": "message",
      "role": "assistant",
      "content": [
        {
          "type": "output_text",
          "text": "The response text spoken by Alexa"
        }
      ]
    }
  ]
}
```

Conversation continuity is maintained server-side: the skill stores the `id` from each response and passes it as `previous_response_id` on the next turn. When the skill is reopened, `previous_response_id` is reset to `null`, starting a fresh conversation.

## Test the Lambda Function

- In the Lambda console, go to the `Test` tab.
- Create a new test event using the `test.json` file from the `doc/` folder of this repository.
- Click `Test` and verify the response is a valid Alexa response JSON.

  ![](images/lambda_test.png)

## Configure the Skill Service Endpoint

- Return to the [Alexa Developer Console](https://developer.amazon.com/alexa/console/ask).
- In the left navigation, go to `CUSTOM` > `Endpoint`.
- Select `AWS Lambda ARN` and paste your Lambda function ARN into the `Default Region` field.
- Click `Save Endpoints`.

  ![](images/skill_endpoint.png)

- In the left navigation, click `Invocation` > `Build Skill` to rebuild the interaction model.

## Enabling the Skill on the Alexa App

- Open the Alexa app on your phone.
- Go to `More` > `Skills & Games` > `Your Skills` > `Dev`.
- Find your skill and tap `Enable`.
- No account linking is required — the API key is configured directly in Lambda.

## Alexa Locale

The skill automatically loads the correct language strings based on the locale of your Alexa account. If your locale is not in the `locale/` folder, it falls back to `en-US`.

Available locales: `de-DE`, `en-CA`, `en-GB`, `en-US`, `es-ES`, `es-MX`, `fr-FR`, `it-IT`, `nl-NL`, `pl-PL`, `pt-BR`, `pt-PT`, `ru-RU`, `sk-SK`.

To add a new language, copy `locale/en-US.lang`, translate the values, and name the file after your locale (e.g. `locale/ja-JP.lang`). Open a PR or issue to contribute it back.
