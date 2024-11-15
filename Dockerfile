FROM python:3.12
ARG COPILOT_ENV
ENV PYTHONUNBUFFERED=1
ENV COPILOT_ENV=${COPILOT_ENV} 
RUN mkdir iiq
COPY . /iiq
RUN pip3 install -r /iiq/requirements.txt --root-user-action
CMD stdbuf -oL python -u /iiq/__main__.py --${COPILOT_ENV}