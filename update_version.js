// A script to do js version update with build number
// First param - project dir path
// Second param - update type (major, minor, patch)
// Third param - CircleCI build number
// Fourth param (Optional) - Manually set version w/o CircleCI build number
const UPDATE_TYPES = ['major', 'minor', 'patch', 'manual']

const args = process.argv.slice(2)
const path = args[0]
const updateType = args[1]
const circleCIBuildNum = args[2]
const manualVersion = args[3]

if (!UPDATE_TYPES.includes(updateType)) {
    throw new Error(`Unknown update type ${updateType}. Possible variants are: ${UPDATE_TYPES.toString()}`)
}

const exec = require('child_process').exec
const config = require(`./${path}/package.json`)
const currentVersion = config["version"]

const incVersion = (currentVersion) => {
    try {
        const newVersion = Number.parseInt(currentVersion) + 1
        return newVersion
    } catch (e) {
        throw new Error(`Current version is not a number, details: ${e.toString()}`)
    }
}

const assembleVersion = (major, minor, patch) => {
    return `${major}.${minor}.${patch}+${circleCIBuildNum}`
}

if (currentVersion === undefined || currentVersion === null) {
    throw new Error("Unknown version, please check path to project directory!")
}
if (updateType === "manual" && !manualVersion) {
    throw new Error("Choosing to set version manually, please, supply it as a 4-th param")
}

const [major, minor, patch] = currentVersion.split(".")
let newVersion = ""
if (updateType === "major") {
    newVersion = assembleVersion(incVersion(major), minor, patch)
} else if (updateType === "minor") {
    newVersion = assembleVersion(major, incVersion(minor), patch)
} else if (updateType === "patch") {
    newVersion = assembleVersion(major, minor, incVersion(patch))
} else {
    newVersion = `${manualVersion}+${circleCIBuildNum}`
}
const command = `yarn --cwd ${path} version --new-version ${newVersion} --no-git-tag-version --no-commit-hooks >> temp_version.txt`

const child = exec(command, (err, stdout, stderr) => {
    if (err) throw err;
    console.log(`stdout: \n${stdout}`);
    console.log(`stderr: \n${stderr}`);
})
