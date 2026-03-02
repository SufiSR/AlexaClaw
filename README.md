# AlexaClaw — Alexa Skill for OpenAI-Compatible Endpoints (AWS Hosted)

> **Forked from [fabianosan/HomeAssistantAssistAWS](https://github.com/fabianosan/HomeAssistantAssistAWS).**
> A huge thank you to [fabianosan](https://github.com/fabianosan) for building such a clean, well-structured foundation — it made adapting this into AlexaClaw remarkably straightforward. Go give that repo a star!

An Alexa skill that routes voice queries to any OpenAI-compatible API endpoint, enabling fully custom AI assistants powered by your own backend.

---

_Note: This project is in active development. Features and configuration may change between releases._

### Table of Contents

1. [About](#about)
2. [Features](#features)
3. [Installation](#installation)
4. [How to use](#how-to-use)
5. [Supported languages](#supported-languages)

## About

AlexaClaw is an AWS-hosted Alexa skill that forwards your spoken queries to an OpenAI-compatible HTTP endpoint — such as `alexa.fluxato.com` — and speaks the response back to you. It maintains multi-turn conversation history within each session and supports Echo Show devices with a welcome screen.

The skill is hosted as an AWS Lambda function, meaning there is **no 8-second Alexa response limit** — a progressive acknowledgment sound is sent immediately while the AI processes your request in the background.

## Features

- **Voice query forwarding** — sends queries to any OpenAI-compatible endpoint (`POST /v1/chat/completions`)
- **Multi-turn conversations** — maintains the full message history across turns within a session
- **Optional system prompt** — configure a custom system prompt via environment variable
- **Progressive acknowledgment** — plays "One moment please" while waiting for the AI response, bypassing Alexa's 8-second timeout
- **Echo Show support** — displays a branded welcome screen on screen-enabled Alexa devices
- **Multi-language support** — see [Supported languages](#supported-languages)
- **Configurable behavior** — ask for follow-up commands, suppress greeting, and more

## Installation

For setup instructions refer to the [installation guide](doc/en/INSTALLATION.md) or [update guide](doc/en/UPDATE.md).

## How to use

- Say `Alexa, open alexa claw` (or your configured skill invocation name):
    - What is the weather like today?
    - Tell me a joke.
    - Summarize the news.

- Or say `Alexa, ask alexa claw what is the capital of France`

## Supported languages

The skill supports the following languages:

- German (Germany)
- English (Australia)
- English (Canada)
- English (England)
- English (United States)
- Dutch (Netherlands)
- Spanish (Spain)
- Spanish (Mexico)
- Spanish (United States)
- French (Canada)
- French (France)
- Italian (Italy)
- Polish (Poland)
- Portuguese (Brazil)
- Portuguese (Portugal)
- Russian (Russia)
- Slovak (Slovakia)

Note: If your language is not supported, open an issue and attach your own version of [en-US.lang](lambda_functions/locale/en-US.lang).

---

# AlexaClaw — Alexa Skill para Endpoints Compatíveis com OpenAI (AWS Hospedado)

> **Bifurcado de [fabianosan/HomeAssistantAssistAWS](https://github.com/fabianosan/HomeAssistantAssistAWS).**
> Um grande obrigado a [fabianosan](https://github.com/fabianosan) por construir uma base tão limpa e bem estruturada — isso tornou a adaptação para o AlexaClaw notavelmente simples. Vá dar uma estrela naquele repositório!

Uma skill Alexa que encaminha consultas de voz para qualquer endpoint de API compatível com OpenAI, permitindo assistentes de IA totalmente personalizados alimentados pelo seu próprio backend.

---

_Nota: Este projeto está em desenvolvimento ativo. Recursos e configurações podem mudar entre versões._

### Índice

1. [Sobre](#sobre)
2. [Recursos](#recursos)
3. [Instalação](#instalação)
4. [Como usar](#como-usar)
5. [Idiomas suportados](#idiomas-suportados)

## Sobre

AlexaClaw é uma skill Alexa hospedada na AWS que encaminha suas consultas de voz para um endpoint HTTP compatível com OpenAI — como `alexa.fluxato.com` — e reproduz a resposta para você. Mantém o histórico de conversa multi-turno em cada sessão e oferece suporte a dispositivos Echo Show com uma tela de boas-vindas.

A skill é hospedada como uma função AWS Lambda, o que significa que **não há limite de 8 segundos de resposta da Alexa** — um som de confirmação progressivo é enviado imediatamente enquanto a IA processa sua solicitação em segundo plano.

## Recursos

- **Encaminhamento de consultas de voz** — envia consultas para qualquer endpoint compatível com OpenAI (`POST /v1/chat/completions`)
- **Conversas multi-turno** — mantém o histórico completo de mensagens entre turnos dentro de uma sessão
- **Prompt de sistema opcional** — configure um prompt de sistema personalizado via variável de ambiente
- **Confirmação progressiva** — reproduz "Um momento por favor" enquanto aguarda a resposta da IA, contornando o timeout de 8 segundos da Alexa
- **Suporte ao Echo Show** — exibe uma tela de boas-vindas em dispositivos Alexa com tela
- **Suporte a vários idiomas** — veja [Idiomas suportados](#idiomas-suportados)
- **Comportamento configurável** — solicitar comandos de acompanhamento, suprimir saudação e mais

## Instalação

Para instruções de configuração, consulte o [guia de instalação](doc/pt/INSTALLATION.md) ou o [guia de atualização](doc/pt/UPDATE.md).

## Como usar

- Diga `Alexa, abrir alexa claw` (ou o nome de invocação configurado para a skill):
    - Como está o tempo hoje?
    - Me conta uma piada.
    - Resuma as notícias.

- Ou diga `Alexa, peça para alexa claw qual é a capital da França`

## Idiomas suportados

A skill tem suporte para os seguintes idiomas:

- Alemão (Alemanha)
- Inglês (Austrália)
- Inglês (Canadá)
- Inglês (Inglaterra)
- Inglês (Estados Unidos)
- Espanhol (Espanha)
- Espanhol (México)
- Espanhol (Estados Unidos)
- Francês (Canadá)
- Francês (França)
- Italiano (Itália)
- Holandês (Holanda)
- Polonês (Polônia)
- Português (Brasil)
- Português (Portugal)
- Russo (Rússia)
- Eslovaco (Eslováquia)
