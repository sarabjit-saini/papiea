#!/usr/bin/env bash
set -e
# This is a script that updates typescript SDK, prints out
# Typescript SDK version, Python commit hash, docker image version
# You use these to update README.md section 'Papiea versions'

circle_num=''
accept=false

function collect_args {

   while [[ $# -gt 0 ]]; do
           case "$1" in
                -circle_num)
                    shift
                    circle_num=$1
                    ;;
                -y)
                    shift
                    accept=true
                    ;;
                *)
                   echo "$1 is not a recognized flag!"
                   return 1;
                   ;;
          esac
          shift
  done

  return 0
}

NPM_REGISTRY=$(npm config list | grep '^registry')
YARN_REGISTRY=$(yarn config get registry)

if [[ "$NPM_REGISTRY" != 'registry = "https://nutanix.jfrog.io/nutanix/api/npm/npm-virtual/"' ]]
then
  echo "Your npm registry is not set to nutanix jfrog!"
  exit 1
fi

if [[ "$YARN_REGISTRY" != "https://nutanix.jfrog.io/nutanix/api/npm/npm-virtual/" ]]
then
  echo "Your yarn registry is not set to nutanix jfrog!"
  exit 1
fi

collect_args "$@" || { echo 'Could not collect args'; exit 1; }

if [[ -z "${CIRCLE_BUILD_NUM}" ]]; then
  if [ -z "$circle_num" ]; then
    echo 'CircleCI build number not specified neither in CIRCLE_BUILD_NUM nor in -circle_num arg.'
    exit 1
  else
    echo 'Using CircleCI build number specified in -circle_num arg'
  fi
else
  echo 'Using CircleCI build number specified in CIRCLE_BUILD_NUM'
  circle_num="${CIRCLE_BUILD_NUM}"
fi

make update_typescript_versions UPD_TYPE="patch" BUILD_NUM="'$circle_num'"
node publish-papiea.js

typescipt_version=$(grep -m 1 'New version' temp_version.txt | sed 's/[a-zA-Z :]*//')
python_version=$(git rev-parse HEAD)

python3 ./papiea-engine/publish-images.py "$typescipt_version"

# sed command is different in BSD (Mac OS) and Linux
# In our case the difference is '-i' flag
# Thus checking the OS type
if [[ "$OSTYPE" == "darwin"* ]]; then
  sed -i '' "/Client\/SDK (typescript)/c\\
  | Client/SDK (typescript)  | $typescipt_version |
  " README.md

  sed -i '' "/Client\/SDK (python)/c\\
  | Client/SDK (python)  | $python_version |
  " README.md

  sed -i '' "/Engine (docker)/c\\
  | Engine (docker) | $typescipt_version |
  " README.md
else
  sed -i "/Client\/SDK (typescript)/c\\
  | Client/SDK (typescript)  | $typescipt_version |
  " README.md

  sed -i "/Client\/SDK (python)/c\\
  | Client/SDK (python)  | $python_version |
  " README.md

  sed -i "/Engine (docker)/c\\
  | Engine (docker) | $typescipt_version |
  " README.md
fi

echo "Python commit hash: $python_version ; Typescript version: $typescipt_version; Circle build number: $circle_num."

if [[ "$accept" != true ]]; then
  while true; do
    read -p "Commit and push? (y/n) " yn
    case $yn in
        [Yy]* ) break;;
        [Nn]* ) exit 1;;
        * ) echo "Please answer yes or no.";;
    esac
  done
fi

git ls-files . | grep 'package\.json' | xargs git add

git add README.md

git commit -m "[skip ci] Upgrade versions. Engine: $circle_num. Typescript: $typescipt_version. Python: $python_version."

git push -u origin HEAD

echo 'Versions updated successfully!'
