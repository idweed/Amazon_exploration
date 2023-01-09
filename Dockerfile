FROM scrapinghub/scrapinghub-stack-scrapy:1.7-py38-latest
RUN apt-get update -y && apt-get upgrade -y && apt-get install zip unzip wget -y

RUN apt-get install libtiff5-dev libjpeg62-turbo-dev libopenjp2-7-dev zlib1g-dev \
    libfreetype6-dev liblcms2-dev libwebp-dev tcl8.6-dev tk8.6-dev python3-tk \
    libharfbuzz-dev libfribidi-dev libxcb1-dev -y

RUN ln -s /usr/bin/python3 /usr/bin/python & \
    ln -s /usr/bin/pip3 /usr/bin/pip

# CMD ["apt-get", "install", "-y", "chromium-browser"]
# RUN locale-gen en_US.UTF-8  
# ENV LANG en_US.UTF-8  
# ENV LANGUAGE en_US:en  
# ENV LC_ALL en_US.UTF-8
# RUN printf "deb http://archive.debian.org/debian/ jessie main\ndeb-src http://archive.debian.org/debian/ jessie main\ndeb http://security.debian.org jessie/updates main\ndeb-src http://security.debian.org jessie/updates main" > /etc/apt/sources.list

# #============================================
# # Google Chrome
# #============================================
# # can specify versions by CHROME_VERSION;
# #  e.g. google-chrome-stable=53.0.2785.101-1
# #       google-chrome-beta=53.0.2785.92-1
# #       google-chrome-unstable=54.0.2840.14-1
# #       latest (equivalent to google-chrome-stable)
# #       google-chrome-beta  (pull latest beta)
# #============================================
# ARG CHROME_VERSION="google-chrome-stable"
# RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add -
# RUN echo "deb http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list
# #RUN apt-get update -qqy --force-yes
# CMD ["apt-get", "update", "-qqy", "--force-yes"]
# #RUN apt-get -qqy install --force-yes ${CHROME_VERSION:-google-chrome-stable}
# CMD ["apt-get", "-qqy","install", "--force-yes", "${CHROME_VERSION:-google-chrome-stable}"]

# RUN rm /etc/apt/sources.list.d/google-chrome.list
# RUN rm -rf /var/lib/apt/lists/* /var/cache/apt/*



# #============================================
# # Chrome webdriver
# #============================================
# # can specify versions by CHROME_DRIVER_VERSION
# # Latest released version will be used by default
# #============================================
# #RUN wget -q https://chromedriver.storage.googleapis.com/71.0.3578.137/chromedriver_linux64.zip && \
# #    unzip chromedriver_linux64.zip && \
# #    chmod +x chromedriver && \
# #    mv chromedriver /usr/bin && \
# #    rm chromedriver_linux64.zip

# RUN wget -q https://chromedriver.storage.googleapis.com/95.0.4638.69/chromedriver_linux64.zip && \
#     unzip chromedriver_linux64.zip && \
#     chmod +x chromedriver && \
#     mv chromedriver /usr/bin && \
#     rm chromedriver_linux64.zip

# install google chrome
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add -
RUN sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list'
RUN apt-get -y update
RUN apt-get install -y google-chrome-stable

# install chromedriver
RUN apt-get install -yqq unzip
RUN wget -O /tmp/chromedriver.zip http://chromedriver.storage.googleapis.com/`curl -sS chromedriver.storage.googleapis.com/LATEST_RELEASE`/chromedriver_linux64.zip
RUN unzip /tmp/chromedriver.zip chromedriver -d /usr/local/bin/

ENV TERM xterm
ENV SCRAPY_SETTINGS_MODULE fnac_screenshots.settings
RUN mkdir -p /app

# install packages required by pillow
RUN apt-get install -y  libxt6 libx11-xcb1 libgtk-3-0 libfreetype6-dev



WORKDIR /app
COPY ./requirements.txt /app/requirements.txt
RUN easy_install distribute && pip install --upgrade distribute
#RUN ["pip", "install", "--no-cache-dir", "-r", "requirements.txt"]
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --upgrade pillow
RUN sudo python -m pip install gcloud
COPY . /app
RUN echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] http://packages.cloud.google.com/apt cloud-sdk main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list && curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | tee /usr/share/keyrings/cloud.google.gpg && apt-get update -y && apt-get install google-cloud-sdk -y
RUN python setup.py install
