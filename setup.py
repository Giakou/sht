from setuptools import setup, find_packages

author = 'Georgios Giakoustidis'
author_email = 'georgios.giakoustidis94@gmail.com'

with open('VERSION') as version_file:
    version = version_file.read().strip()

with open('requirements.txt') as f:
    install_requires = f.read().splitlines()

setup(
    name="sht85",
    version=version,
    python_requires='>=3.0',
    description='Python wrapper library of Adafruit_PureIO.smbus for Sensirion SHT85 sensors',
    url='https://github.com/Giakou/sht85.git',
    license='GNU GPL',
    long_description='Python wrapper library of Adafruit_PureIO.smbus for Sensirion SHT85 sensors connected to I2c pins'
                     ' of a Raspberrry Pi',
    install_requires=install_requires,
    author=author,
    maintainer=author,
    author_email=author_email,
    packages=find_packages(),
    platforms='any'
)
