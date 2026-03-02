
# ATUALIZAÇÃO

## Atualizando a Skill
1. Navegue até o [AWS Lambda console](https://us-east-1.console.aws.amazon.com/lambda/home), clique na sua função:
   - Na parte direita, clique em `Upload from` e selecione `Zip file`;

      ![](../en/images/update01.png)

2. Depois clique em `Save`;

      ![](../en/images/update02.png)

3. **Atenção** — revise o log de atualizações da versão ou as [instruções de instalação](INSTALLATION.md) para verificar se alguma variável de ambiente foi alterada ou adicionada. Em particular, verifique se `openclaw_url` e `openclaw_api_key` ainda estão configuradas corretamente.
4. As alterações têm efeito imediato. Teste na sua Alexa mais próxima. Se não surtir efeito, clique em `Deploy` conforme a imagem abaixo:

   ![](../en/images/update03.png)

5. Feito!
