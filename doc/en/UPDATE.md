
# UPDATE

## Updating the Skill
1. Navigate to the [AWS Lambda console](https://us-east-1.console.aws.amazon.com/lambda/home), and click on your function:
   - On the right side, click `Upload from` and select `Zip file`;

      ![](images/update01.png)

2. Then click `Save`;

      ![](images/update02.png)

3. **Important** — review the version update log or the [installation instructions](INSTALLATION.md) to check if any environment variables have been changed or added. In particular, verify that `openclaw_url` and `openclaw_api_key` are still set correctly.
4. The changes take effect immediately. Test it on your nearest Alexa device. If it works, click `Deploy` as shown in the image below:

   ![](images/update03.png)

5. Done!
