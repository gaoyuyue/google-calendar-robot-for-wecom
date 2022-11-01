# To enable ssh & remote debugging on app service change the base image to the one below
# FROM mcr.microsoft.com/azure-functions/python:4-python3.9-appservice as base
FROM mcr.microsoft.com/azure-functions/python:4-python3.9 as base

ENV AzureWebJobsScriptRoot=/home/site/wwwroot \
    AzureFunctionsJobHost__Logging__Console__IsEnabled=true

FROM base AS python-deps
RUN pip install pipenv
COPY Pipfile* /
RUN PIPENV_VENV_IN_PROJECT=1 pipenv install

FROM base AS runtime
COPY --from=python-deps /.venv /.venv
ENV PATH="/.venv/bin:$PATH"

COPY . /home/site/wwwroot