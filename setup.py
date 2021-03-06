from setuptools import setup

setup(
    name="iboot",
    version="0.1.0",
    author="Luke Fitzgerald",
    author_email="",
    description=("Python library to control iBoot."),
    license="BSD",
    keywords="python iboot",
    url="https://github/darkip/iboot",
    packages=['iboot'],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Topic :: Utilities",
        "License :: OSI Approved :: BSD License",
    ],
    entry_points = {
      'console_scripts':[
      'ibootpy = iboot.iboot:run',
      ]
    },
)
