from setuptools import setup, find_packages

setup(
    name='Bac1',
    version='2025.7.11',
    description='BACnet Device Management with BACpypes3',
    author='BACnet Development Team',
    author_email='support@bacnet.dev',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'bacpypes3>=0.0.102',
        'python-dotenv>=1.0.0',
        'asyncio>=3.4.3',
    ],
    python_requires='>=3.10',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Topic :: Communications',
        'Topic :: System :: Networking',
    ],
    keywords='bacnet building-automation hvac control',
    project_urls={
        'Source': 'https://github.com/bacnet/bac1',
        'Documentation': 'https://bacnet.dev/docs',
    },
) 