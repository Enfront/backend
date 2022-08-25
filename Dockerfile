# pull official base image
FROM python:3.10.5-slim-buster as dev

# set working directory
WORKDIR /usr/src/app

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# run virtual environment
ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# update environment
RUN apt-get update \
    && apt-get -y install libpq-dev gcc

# install dependencies
RUN pip3 install --upgrade pip
COPY ./requirements.txt .
RUN pip3 install -r requirements.txt

# add app
COPY . .

# run migrations
ENTRYPOINT ["bash", "docker-entrypoint.sh"]

# start app
CMD ["python3", "manage.py", "runserver", "0.0.0.0:8000", "--settings" , "api.settings.dev"]

# pull official base image
FROM python:3.10.5-slim-buster as staging

# set working directory
WORKDIR /usr/src/app

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# run virtual environment
ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# update environment
RUN apt-get update \
    && apt-get -y install libpq-dev gcc

# install dependencies
RUN pip3 install --upgrade pip
COPY ./requirements.txt .
RUN pip3 install -r requirements.txt

# add app
COPY . .

# run migrations
ENTRYPOINT ["bash", "docker-entrypoint.sh"]

# start app
CMD ["python3", "manage.py", "runserver", "0.0.0.0:8000", "--settings" , "api.settings.staging"]

# pull official base image
FROM python:3.10.5-slim-buster as prod

# set working directory
WORKDIR /usr/src/app

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# run virtual environment
ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# update environment
RUN apt-get update \
    && apt-get -y install libpq-dev gcc

# install dependencies
RUN pip3 install --upgrade pip
COPY ./requirements.txt .
RUN pip3 install -r requirements.txt

# add app
COPY . .

# run migrations
ENTRYPOINT ["bash", "docker-entrypoint.sh"]

# start app
CMD ["gunicorn", "--bind", ":8000", "--workers", "3", "api.wsgi:application"]
