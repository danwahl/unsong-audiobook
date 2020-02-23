1. Create Python virtual environment using [virtualenvwrapper](https://virtualenvwrapper.readthedocs.io/en/latest/):

```sh
mkvirtualenv --python=/usr/bin/python3 unsong_audiobook
pip install -r scripts/requirements.txt
```

2. Create file `scripts/aws_access.sh` with AWS key information:

```sh
#!/bin/sh
export AWS_ACCESS_KEY_ID="..."
export AWS_SECRET_ACCESS_KEY="..."
```

3. Activate virtual environment and run script:

```sh
workon unsong_audiobook
cd scripts
source aws_access.sh
python unsong_audiobook.py
```
