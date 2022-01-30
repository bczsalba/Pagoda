from setuptools import setup

setup(
    name="pagoda",
    version="0.0.0",
    include_package_data=True,
    packages=["pagoda"],
    license="MIT",
    description="",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    install_requires=["pytermgui==2.0.0"],
    python_requires=">=3.7.0",
    url="https://github.com/bczsalba/pagoda",
    author="BcZsalba",
    author_email="bczsalba@gmail.com",
    entry_points={"console_scripts": ["pagoda=pagoda.__main__:main"]},
)
