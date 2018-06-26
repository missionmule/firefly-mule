from setuptools import setup

setup(name='firefly-mule',
      version='0.1.0',
      description='Companion computer avionics package for BirdsEyeView FireFLY6 PRO',
      classifiers=[
        'Development Status :: 3 - Alpha',
        'Programming Language :: Python :: 3.6',
      ],
      url='https://github.com/missionmule/firefly-mule',
      author='Zane Mountcastle',
      author_email='zane@missionmule.com',
      packages=['firefly-mule'],
      python_requires='>=3.6',
      install_requires=[
          'paramiko',
          'pyserial',
          'pytest-runner'
      ],
      tests_require='pytest',
      test_suite='tests',
      zip_safe=False)
