# Image: https://github.com/OSGeo/gdal/tree/master/docker
FROM osgeo/gdal:ubuntu-small-latest

# Install pip for PyPI installs
RUN apt-get update --fix-missing
RUN apt-get install -y python3-pip

RUN pip install --upgrade pip
COPY requirements.txt ./requirements.txt
RUN pip install -r requirements.txt

COPY . ./

CMD ["gunicorn", "app:server"]