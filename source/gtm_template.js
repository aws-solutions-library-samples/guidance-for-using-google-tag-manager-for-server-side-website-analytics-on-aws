// Original source code is from GTM template library https://help.stape.io/hc/en-us/articles/6093296436125-JSON-HTTP-request
const sendHttpRequest = require('sendHttpRequest');
const getAllEventData = require('getAllEventData');
const makeInteger = require('makeInteger');
const makeTableMap = require('makeTableMap');
const JSON = require('JSON');
const getRequestHeader = require('getRequestHeader');
const logToConsole = require('logToConsole');
const getContainerVersion = require('getContainerVersion');
const containerVersion = getContainerVersion();
const isDebug = containerVersion.debugMode;
const isLoggingEnabled = determinateIsLoggingEnabled();
const traceId = getRequestHeader('trace-id');

const postHeaders = {'Content-Type': 'application/json'};
let postBodyData = {};

if (data.includeEventData) {
    // This is the changge from the original template
    // producer service expects a key "data" in the request payload
    postBodyData.data = getAllEventData();
}

if (data.headers) {
    for (let key in data.headers) {
        postHeaders[data.headers[key].key] = data.headers[key].value;
    }
}

if (data.data) {
    let postBodyCustomData = data.simple_object ? createSimpleObject() : createNestedObject();

    for (let key in postBodyCustomData) {
        postBodyData[key] = postBodyCustomData[key];
    }
}

if (data.flatten) {
    postBodyData = escapeKeys(flatten(postBodyData));
}

if (data.inside_array) {
    postBodyData = [postBodyData];
}

const postBody = JSON.stringify(postBodyData);
let requestOptions = {headers: postHeaders, method: data.requestMethod};

if (data.requestTimeout) {
    requestOptions.timeout = makeInteger(data.requestTimeout);
}

if (isLoggingEnabled) {
    logToConsole(JSON.stringify({
        'Name': 'JsonRequest',
        'Type': 'Request',
        'TraceId': traceId,
        'RequestMethod': data.requestMethod,
        'RequestUrl': data.url,
        'RequestBody': postBodyData,
    }));
}

sendHttpRequest(data.url, (statusCode, headers, body) => {
    if (isLoggingEnabled) {
        logToConsole(JSON.stringify({
            'Name': 'JsonRequest',
            'Type': 'Response',
            'TraceId': traceId,
            'ResponseStatusCode': statusCode,
            'ResponseHeaders': headers,
            'ResponseBody': body,
        }));
    }

    if (statusCode >= 200 && statusCode < 300) {
        data.gtmOnSuccess();
    } else {
        data.gtmOnFailure();
    }
}, requestOptions, postBody);


function escapeKeys(ob) {
    var toReturn = {};

    for (let key in ob) {
        let newKey = key.split("-").join("_");

        toReturn[newKey] = ob[key];
    }

    return toReturn;
}

function flatten(ob) {
    var toReturn = {};

    for (let i in ob) {
        if (!ob.hasOwnProperty(i)) continue;

        if ((typeof ob[i]) == 'object') {
            var flatObject = flatten(ob[i]);
            for (var x in flatObject) {
                if (!flatObject.hasOwnProperty(x)) continue;

                toReturn[i + '_' + x] = flatObject[x];
            }
        } else {
            toReturn[i] = ob[i];
        }
    }
    return toReturn;
}

function createSimpleObject() {
    return makeTableMap(data.data, 'key', 'value');
}


function mergeObjects() {
    let obj = {},
        i = 0,
        il = arguments.length,
        key;
    for (; i < il; i++) {
        for (key in arguments[i]) {
            if (arguments[i][key]) {
                obj[key] = arguments[i][key];
            }
        }
    }
    return obj;
}

function createNestedObject() {
    let object = {};

    for (let key in data.data) {
        let dotPath = data.data[key].key;
        let rootProperty = dotPath.split('.')[0];
        let strObj = strToObj(dotPath, data.data[key].value)[rootProperty];

        if (object[rootProperty]) {
            object[rootProperty] = mergeObjects(object[rootProperty], strObj);
        } else {
            object[rootProperty] = strObj;
        }
    }

    return object;
}

function strToObj(dotPath, val) {
    let i, obj = {}, dotArr = dotPath.split('.');
    let x = obj;

    for (i = 0; i < dotArr.length - 1; i++) {
        x = x[dotArr[i]] = {};
    }

    x[dotArr[i]] = val;

    return obj;
}

function determinateIsLoggingEnabled() {
    if (!data.logType) {
        return isDebug;
    }

    if (data.logType === 'no') {
        return false;
    }

    if (data.logType === 'debug') {
        return isDebug;
    }

    return data.logType === 'always';
}