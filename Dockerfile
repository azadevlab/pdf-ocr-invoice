#stage 1 - build
FROM python:3.10.7-slim as build_stage
LABEL Azamat Kyrykbayev, @azadevlab

WORKDIR /wheel/code
COPY code/ /wheel/code

RUN sed -i '/bs4/ s/^#*/#/' requirements.txt \
    && pip wheel -r requirements.txt -w /wheel \
    && sed -i '/bs4/s/^#//g' requirements.txt


# stage 2 - final
FROM python:3.10.7-slim
COPY --from=build_stage /wheel /wheel

RUN mv /wheel/code / \
    && pip install /wheel/* \
    && rm -rf /wheel
    # && pip cache dir \
    # && pip cache purge
WORKDIR /code

ENTRYPOINT ["python", "main.py", "invoice.pdf"]
