"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.THROW = THROW;
exports.ASSERT = ASSERT;
exports.CONDITIONALASSERT = CONDITIONALASSERT;
exports.PARAMCHECK = PARAMCHECK;
exports.CONDITIONALPARAMCHECK = CONDITIONALPARAMCHECK;
exports.INVALIDPLAYLIST = INVALIDPLAYLIST;
exports.toNumber = toNumber;
exports.hexToByteSequence = hexToByteSequence;
exports.byteSequenceToHex = byteSequenceToHex;
exports.tryCatch = tryCatch;
exports.splitAt = splitAt;
exports.trim = trim;
exports.splitByCommaWithPreservingQuotes = splitByCommaWithPreservingQuotes;
exports.camelify = camelify;
exports.formatDate = formatDate;
exports.hasOwnProp = hasOwnProp;
exports.setOptions = setOptions;
exports.getOptions = getOptions;
let options = {};
function THROW(err) {
    if (!options.strictMode) {
        if (!options.silent) {
            console.error(err.message);
        }
        return;
    }
    throw err;
}
function ASSERT(msg, ...options) {
    for (const [index, param] of options.entries()) {
        if (!param) {
            THROW(new Error(`${msg} : Failed at [${index}]`));
        }
    }
}
function CONDITIONALASSERT(...options) {
    for (const [index, [cond, param]] of options.entries()) {
        if (!cond) {
            continue;
        }
        if (!param) {
            THROW(new Error(`Conditional Assert : Failed at [${index}]`));
        }
    }
}
function PARAMCHECK(...options) {
    for (const [index, param] of options.entries()) {
        if (param === undefined) {
            THROW(new Error(`Param Check : Failed at [${index}]`));
        }
    }
}
function CONDITIONALPARAMCHECK(...options) {
    for (const [index, [cond, param]] of options.entries()) {
        if (!cond) {
            continue;
        }
        if (param === undefined) {
            THROW(new Error(`Conditional Param Check : Failed at [${index}]`));
        }
    }
}
function INVALIDPLAYLIST(msg) {
    THROW(new Error(`Invalid Playlist : ${msg}`));
}
function toNumber(str, radix = 10) {
    if (typeof str === 'number') {
        return str;
    }
    const num = radix === 10 ? Number.parseFloat(str) : Number.parseInt(str, radix);
    if (Number.isNaN(num)) {
        return 0;
    }
    return num;
}
function hexToByteSequence(str) {
    if (str.startsWith('0x') || str.startsWith('0X')) {
        str = str.slice(2);
    }
    const numArray = new Uint8Array(str.length / 2);
    for (let i = 0; i < str.length; i += 2) {
        numArray[i / 2] = Number.parseInt(str.slice(i, i + 2), 16);
    }
    return numArray;
}
function byteSequenceToHex(sequence, start = 0, end = sequence.byteLength) {
    if (end <= start) {
        THROW(new Error(`end must be larger than start : start=${start}, end=${end}`));
    }
    const array = [];
    for (let i = start; i < end; i++) {
        array.push(`0${(sequence[i] & 0xFF).toString(16).toUpperCase()}`.slice(-2));
    }
    return `0x${array.join('')}`;
}
function tryCatch(body, errorHandler) {
    try {
        return body();
    }
    catch (err) {
        return errorHandler(err);
    }
}
function splitAt(str, delimiter, index = 0) {
    let lastDelimiterPos = -1;
    for (let i = 0, j = 0; i < str.length; i++) {
        if (str[i] === delimiter) {
            if (j++ === index) {
                return [str.slice(0, i), str.slice(i + 1)];
            }
            lastDelimiterPos = i;
        }
    }
    if (lastDelimiterPos !== -1) {
        return [str.slice(0, lastDelimiterPos), str.slice(lastDelimiterPos + 1)];
    }
    return [str];
}
function trim(str, char = ' ') {
    if (!str) {
        return str;
    }
    str = str.trim();
    if (char === ' ') {
        return str;
    }
    if (str.startsWith(char)) {
        str = str.slice(1);
    }
    if (str.endsWith(char)) {
        str = str.slice(0, -1);
    }
    return str;
}
function splitByCommaWithPreservingQuotes(str) {
    const list = [];
    let doParse = true;
    let start = 0;
    const prevQuotes = [];
    for (let i = 0; i < str.length; i++) {
        const curr = str[i];
        if (doParse && curr === ',') {
            list.push(str.slice(start, i).trim());
            start = i + 1;
            continue;
        }
        if (curr === '"' || curr === '\'') {
            if (doParse) {
                prevQuotes.push(curr);
                doParse = false;
            }
            else if (curr === prevQuotes.at(-1)) {
                prevQuotes.pop();
                doParse = true;
            }
            else {
                prevQuotes.push(curr);
            }
        }
    }
    list.push(str.slice(start).trim());
    return list;
}
function camelify(str) {
    const array = [];
    let nextUpper = false;
    for (const ch of str) {
        if (ch === '-' || ch === '_') {
            nextUpper = true;
            continue;
        }
        if (nextUpper) {
            array.push(ch.toUpperCase());
            nextUpper = false;
            continue;
        }
        array.push(ch.toLowerCase());
    }
    return array.join('');
}
function formatDate(date) {
    const YYYY = date.getUTCFullYear();
    const MM = ('0' + (date.getUTCMonth() + 1)).slice(-2);
    const DD = ('0' + date.getUTCDate()).slice(-2);
    const hh = ('0' + date.getUTCHours()).slice(-2);
    const mm = ('0' + date.getUTCMinutes()).slice(-2);
    const ss = ('0' + date.getUTCSeconds()).slice(-2);
    const msc = ('00' + date.getUTCMilliseconds()).slice(-3);
    return `${YYYY}-${MM}-${DD}T${hh}:${mm}:${ss}.${msc}Z`;
}
function hasOwnProp(obj, propName) {
    return Object.hasOwn(obj, propName);
}
function setOptions(newOptions = {}) {
    options = Object.assign(options, newOptions);
}
function getOptions() {
    return Object.assign({}, options);
}
