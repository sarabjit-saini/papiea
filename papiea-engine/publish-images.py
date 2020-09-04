#!/usr/bin/env python
import subprocess
import os
import sys

BASE_TAG = "nutanix-docker.jfrog.io/papiea:"


def construct_tags(sem_ver):
    tags = []
    sem_ver_parts = sem_ver.split("+")
    major, minor, patch = sem_ver_parts[0].split(".")
    tags.append(major)
    tags.append(f"{BASE_TAG}{major}.{minor}")
    tags.append(f"{BASE_TAG}{major}.{minor}.{patch}")
    try:
        version, build_num = sem_ver_parts[0], sem_ver_parts[1]
        if build_num != os.environ['CIRCLE_BUILD_NUM']:
            raise Exception("Environment variable and version param CI build number mismatch!")
        tags.append(f"{BASE_TAG}{version}+{build_num}")
    except IndexError as e:
        print(f"No build number present in the version: {sem_ver}")
        pass
    return tags


build_tag = (BASE_TAG + os.environ['CIRCLE_BUILD_NUM'])

subprocess.check_call([
    'docker', 'login',
    'nutanix-docker.jfrog.io',
    '-u', os.environ['ARTIFACTORY_USER'],
    '-p', os.environ['ARTIFACTORY_PASSWORD']])

with open(".dockerignore", "w") as f:
    f.write("!papiea-engine/__tests__/test_data_factory.ts")
    f.write("papiea-engine/__tests__/**/*")
    f.write("papiea-engine/__benchmarks__/**/*")

subprocess.check_call([
    'docker', 'build',
    '-t', build_tag,
    '-f', '.circleci/Dockerfile',
    '.'])

subprocess.check_call(['docker', 'push', build_tag])
# if os.environ['CIRCLE_BRANCH'] == 'master':
try:
    semantic_version = sys.argv[1]
except IndexError as e:
    print("No semantic version was passed as an argument, aborting")
    sys.exit(1)
latest_tag = f"{BASE_TAG}latest"
# subprocess.check_call([
#     'docker', 'tag', build_tag, latest_tag])
# subprocess.check_call(['docker', 'push', latest_tag])
tags = construct_tags(semantic_version)
for tag in tags:
    print(f"Publishing {tag}")
    subprocess.check_call([
        'docker', 'tag', build_tag, tag])
    subprocess.check_call(['docker', 'push', tag])
