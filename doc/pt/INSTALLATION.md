# INSTALAÇÃO

## Índice
1. [Requisitos](#requisitos)
2. [Criar uma Skill Amazon Alexa](#criar-uma-skill-amazon-alexa)
3. [Criar uma Função AWS Lambda](#criar-uma-função-aws-lambda)
4. [Adicionar Código à Função Lambda](#adicionar-código-à-função-lambda)
5. [Configurar Variáveis de Ambiente](#configurar-variáveis-de-ambiente)
6. [Testar a Função Lambda](#testar-a-função-lambda)
7. [Configurar o Endpoint do Serviço da Skill](#configurar-o-endpoint-do-serviço-da-skill)
8. [Habilitar a Skill no App Alexa](#habilitar-a-skill-no-app-alexa)
9. [Localização da Alexa](#localização-da-alexa)

---

## Requisitos
- Um endpoint de API compatível com OpenAI acessível via HTTPS (ex.: `https://alexa.fluxato.com`). O endpoint deve implementar `POST /v1/chat/completions`.
- Uma chave de API Bearer para esse endpoint.
- Uma conta de desenvolvedor da Amazon. Inscreva-se [aqui](https://developer.amazon.com/).
- Uma conta Amazon Web Services (AWS) para hospedar a função Lambda. O AWS Lambda é gratuito para até 1 milhão de solicitações e 1 GB de dados por mês.

## Criar uma Skill Amazon Alexa
- Faça login no [Alexa Developer Console](https://developer.amazon.com/alexa/console/ask).
_Nota: Isso deve ser feito com a mesma conta Amazon que você usa nos seus dispositivos Alexa e app._
- Vá para a página `Alexa Skills` e clique em `Create Skill`.
- No passo `Name, Locale`: insira um nome para a skill, selecione o idioma padrão e clique em `Next`. _**Importante**: O idioma da sua skill deve corresponder ao idioma da sua conta Amazon/Alexa. [Mais informações sobre idiomas suportados aqui](../../README.md#idiomas-suportados)_
- No passo `Experience, Model, Hosting service`: selecione `Other` > `Custom` > `Provision your own`, depois clique em `Next`.
- No passo `Template`: selecione `Start from Scratch` e clique em `Next`.
- Revise e clique em `Create Skill`.

  ![](../en/images/skill_review.png)
- Na próxima tela, no painel direito `Building your skill`:

  ![](../en/images/skill_build.png)

  - Clique em `Invocation Name >`, defina o nome de invocação (ex.: `alexa claw`), e clique em `Save`.
  - No menu de navegação à esquerda, vá para `CUSTOM` > `Interaction Model` > `JSON Editor`, arraste e solte o [arquivo interactionModels.json](../interactionModels.json), depois clique em `Save`.

  ![](../en/images/skill_intmodel.png)

  - Ainda no menu de navegação à esquerda, vá para `CUSTOM` > `Interfaces`, role para baixo até `Alexa Presentation Language`, habilite e desmarque `Hub Round` _(não compatível com esta skill)_.

  ![](../en/images/skill_interfaces.png)

  - Vá para `CUSTOM` > `Endpoint` e anote o `Your Skill ID`.
- Mantenha o `Alexa Developer Console` aberto — você precisará dele em um passo posterior.

## Criar uma Função AWS Lambda
A função Lambda recebe as solicitações da Alexa e as encaminha para o seu endpoint compatível com OpenAI.

Faça login no [console AWS](https://aws.amazon.com/console/).

## Adicionar Código à Função Lambda
- No console AWS, navegue até `Lambda` em `Compute`.
- **IMPORTANTE** — Skills Alexa são suportadas apenas em certas regiões da AWS. Selecione a mais próxima:
  - **US East (N. Virginia)** para skills em `English (US)`, `English (CA)`, `Portuguese (BR)`.
  - **EU (Ireland)** para skills em `English (UK)`, `Italian`, `German (DE)`, `Spanish (ES)`, `French (FR)`.
  - **US West (Oregon)** para skills em `Japanese` e `English (AU)`.
- Clique em `Functions` > `Create function`:
  - Selecione `Author from scratch`, insira um nome de função (ex.: `AlexaClaw`).
  - Selecione **Python 3.12** como Runtime e **x86_64** como arquitetura.
  - Deixe a função de execução padrão sem alterações.
- Clique em `Create function`.

  ![](../en/images/lambda_function.png)

- Expanda `Function overview`, clique em `+ Add trigger`, selecione `Alexa` > `Alexa Skills Kit`, insira o `Skill ID` do passo anterior e clique em `Add`.

  ![](../en/images/lambda_trigger.png)

- Role até a aba `Code` > `Code source`, clique em `Upload from` > `zip file`.
- Baixe o zip da versão mais recente na [página de Releases](https://github.com/your-org/AlexaClaw/releases), faça o upload e clique em `Save`.

  ![](../en/images/lambda_code.png)

## Configurar Variáveis de Ambiente

No console da função Lambda, vá para `Configuration` > `Environment variables` e adicione as seguintes:

### Obrigatórias

| Variável | Descrição | Exemplo |
|---|---|---|
| `openclaw_url` | URL base do seu endpoint compatível com OpenAI (sem barra no final) | `https://alexa.fluxato.com` |
| `openclaw_api_key` | Chave de API Bearer para autenticação | `sk-...` |

### Opcionais

| Variável | Padrão | Descrição |
|---|---|---|
| `openclaw_model` | _(nenhum)_ | Nome do modelo a passar no corpo da requisição (ex.: `gpt-4o`) |
| `openclaw_system_prompt` | _(nenhum)_ | Prompt de sistema adicionado no início de cada conversa |
| `ask_for_further_commands` | `False` | Quando `true`, mantém a sessão aberta e pergunta "Mais alguma coisa?" após cada resposta |
| `suppress_greeting` | `False` | Quando `true`, suprime a frase de boas-vindas ao abrir a skill |
| `enable_acknowledgment_sound` | `False` | Quando `true`, reproduz "Um momento por favor" imediatamente enquanto aguarda a resposta da IA — **recomendado para modelos lentos** |
| `debug` | `False` | Quando `true`, ativa o log de depuração detalhado no CloudWatch |

### Como a chamada de API funciona

A skill envia uma requisição `POST` para `{openclaw_url}/v1/responses` usando o formato da Responses API da OpenAI:

```json
{
  "model": "nome-do-seu-modelo",
  "input": "O que o usuário disse",
  "instructions": "Seu prompt de sistema (opcional)",
  "previous_response_id": "resp_abc123 (omitido no primeiro turno)"
}
```

A skill espera uma resposta compatível com a Responses API da OpenAI:

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
          "text": "O texto de resposta falado pela Alexa"
        }
      ]
    }
  ]
}
```

A continuidade da conversa é mantida no servidor: a skill armazena o `id` de cada resposta e o envia como `previous_response_id` no próximo turno. Quando a skill é reaberta, o `previous_response_id` é reiniciado como `null`, iniciando uma nova conversa.

## Testar a Função Lambda

- No console Lambda, vá para a aba `Test`.
- Crie um novo evento de teste usando o arquivo `test.json` da pasta `doc/` deste repositório.
- Clique em `Test` e verifique se a resposta é um JSON de resposta Alexa válido.

  ![](../en/images/lambda_test.png)

## Configurar o Endpoint do Serviço da Skill

- Retorne ao [Alexa Developer Console](https://developer.amazon.com/alexa/console/ask).
- No menu de navegação à esquerda, vá para `CUSTOM` > `Endpoint`.
- Selecione `AWS Lambda ARN` e cole o ARN da sua função Lambda no campo `Default Region`.
- Clique em `Save Endpoints`.

  ![](../en/images/skill_endpoint.png)

- No menu de navegação à esquerda, clique em `Invocation` > `Build Skill` para reconstruir o modelo de interação.

## Habilitar a Skill no App Alexa

- Abra o app Alexa no seu celular.
- Vá para `More` > `Skills & Games` > `Your Skills` > `Dev`.
- Encontre sua skill e toque em `Enable`.
- Nenhuma vinculação de conta é necessária — a chave de API é configurada diretamente no Lambda.

## Localização da Alexa

A skill carrega automaticamente os textos no idioma correto com base na localização da sua conta Alexa. Se a sua localização não estiver na pasta `locale/`, será usado o `en-US` como padrão.

Localizações disponíveis: `de-DE`, `en-CA`, `en-GB`, `en-US`, `es-ES`, `es-MX`, `fr-FR`, `it-IT`, `nl-NL`, `pl-PL`, `pt-BR`, `pt-PT`, `ru-RU`, `sk-SK`.

Para adicionar um novo idioma, copie `locale/en-US.lang`, traduza os valores e nomeie o arquivo com a sua localização (ex.: `locale/ja-JP.lang`). Abra um PR ou issue para contribuir.
