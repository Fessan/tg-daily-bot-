"""
Setup для установки проекта в development режиме
"""
from setuptools import setup, find_packages

setup(
    name="tg-daily-bot",
    version="2.0.0",
    packages=find_packages(),
    py_modules=[
        'main',
        'config',
        'bot_instance',
        'utils',
        'scheduler_tasks',
        'db',
    ],
    install_requires=[
        line.strip()
        for line in open('requirements.txt').readlines()
        if line.strip() and not line.startswith('#')
    ],
)










