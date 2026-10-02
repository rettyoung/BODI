// Build the workbook the console builds, from a console data.json, with ExcelJS in Node.
// usage: node tests/xlsx_build.js data.json out.xlsx
const fs = require("fs");
const ExcelJS = require("exceljs");
const {build} = require("../console/tracker_xlsx.js");
const d = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
build(ExcelJS, d.table, d.asof).xlsx.writeFile(process.argv[3]).then(() => console.log("wrote", process.argv[3]));
