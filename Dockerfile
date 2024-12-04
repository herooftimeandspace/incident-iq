FROM python:3.12
ARG COPILOT_ENV
ENV PYTHONUNBUFFERED=1
ENV COPILOT_ENV=${COPILOT_ENV}
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV TZ="America/Los_Angeles"
RUN mkdir iiq
COPY . /iiq
RUN pip3 install -r /iiq/requirements.txt --root-user-action=ignore
CMD stdbuf -oL python -u /iiq/__main__.py --${COPILOT_ENV}