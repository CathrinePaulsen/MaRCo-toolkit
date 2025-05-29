from setuptools import setup, find_packages

setup(
    name='evaluatelinker',
    version='0.1',
    packages=find_packages(),
    install_requires=[
        'core',
        'server',
        'rq',
        'SQLAlchemy==2.0.23',
        'PyGithub==2.1.1',
        'pandas==2.3.1'
    ],
    extras_require={
        'tests': ['pytest==8.0.0',
                  'mock==5.1.0'
                  ],
    },
    entry_points={
        'console_scripts': [
            'evaluate-linker=evaluatelinker:main',
            'linker-process_linking=linker:process_linking',
            'linker-process_jars=linker:process_tests_jars',
        ]
    }
)
