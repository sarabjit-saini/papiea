// Yarn doesn't yet have npm prune --production analog
// Thus using this script to do it manually
const args = process.argv.slice(2);
const path = args[0]

const exec = require('child_process').exec;
const devDependencies = Object.keys(require(`./${path}/package.json`).devDependencies).join(' ');
const command = `yarn --cwd ${path} remove ` + devDependencies;

const child = exec(command, (err, stdout, stderr) => {
    if (err) throw err;
    console.log(`stdout: \n${stdout}`);
    console.log(`stderr: \n${stderr}`);
});
