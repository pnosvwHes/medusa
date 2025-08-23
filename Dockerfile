FROM python:3.12-bullseye
ENV PYTHONUNBUFFERED=1

RUN mkdir /code

WORKDIR /code

RUN pip install poetry

COPY pyproject.toml poetry.lock* /code/

RUN poetry install --no-root

COPY . /code/

# RUN chmod 755 /code/start-django.sh
EXPOSE 8000

ENTRYPOINT [ "/code/start-django.sh" ]
