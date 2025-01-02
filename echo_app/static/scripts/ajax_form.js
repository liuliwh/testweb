"use strict";

var XHRSubmitForm = function () {
  if (!XMLHttpRequest.prototype.sendAsBinary) {
    XMLHttpRequest.prototype.sendAsBinary = function (datastr) {
      function byteValue(x) {
        return x.charCodeAt(0) & 0xff;
      }
      var ords = Array.prototype.map.call(datastr, byteValue);
      var ui8a = new Uint8Array(ords);
      this.send(ui8a.buffer);
    }
  }

  function submitData(data) {
    var req = new XMLHttpRequest();
    req.submittedData = data;
    req.onload = xhrSuccess;
    if (data.technique === 0) {
      // method is GET
      req.open("get", data.receiver.replace(/(?:\?.*)?$/, data.segments.length > 0 ? "?" + data.segments.join("&") : ""), true);
      req.setRequestHeader('X-IS-AJAX', 'true');
      req.send(null);
    } else {
      // method is POST
      req.open("post", data.receiver, true);
      // indicate is ajax or not
      req.setRequestHeader('X-IS-AJAX', 'true');
      if (data.technique === 3) {
        // enctype is multipart/form-data
        var boundary = "---------------------------" + Date.now().toString(16);
        req.setRequestHeader("Content-Type", "multipart/form-data; boundary=" + boundary);
        req.sendAsBinary("--" + boundary + "\r\n" + data.segments.join("--" + boundary + "\r\n") + ("--" + boundary + "--\r\n"));
      } else {
        // enctype is application/x-www-form-urlencoded or text/plain
        req.setRequestHeader("Content-Type", data.contentType);
        req.send(data.segments.join(data.technique === 2 ? "\r\n" : "&"));
      }
    }
  }

  function processStatus(data, xhrSuccess) {
    if (data.status > 0) {
      return;
    }
    // the form is now totally serialized! do something before sending it to the server…
    // doSomething(data);
    // console.log("XHRSubmit - The form is now serialized. Submitting...");
    submitData(data, xhrSuccess);
  }

  function pushSegment(segment) {
    this.owner.segments[this.segmentIdx] += segment.target.result + "\r\n";
    this.owner.status--;
    processStatus(this.owner);
  }

  function plainEscape(text) {
    // How should I treat a text/plain form encoding?
    // What characters are not allowed? this is what I suppose…:
    // "4\3\7 - Einstein said E=mc2" ----> "4\\3\\7\ -\ Einstein\ said\ E\=mc2"
    return text.replace(/[\s\=\\]/g, "\\$&");
  }

  function SubmitRequest(target, xhrSuccess) {
    var isPost = target.method.toLowerCase() === "post";
    this.contentType = isPost && target.enctype ? target.enctype : "application\/x-www-form-urlencoded";
    this.technique = isPost ? this.contentType === "multipart\/form-data" ? 3 : this.contentType === "text\/plain" ? 2 : 1 : 0;
    this.receiver = target.action;
    this.status = 0;
    this.segments = [];
    var filter = this.technique === 2 ? plainEscape : escape;
    var _iteratorNormalCompletion = true;
    var _didIteratorError = false;
    var _iteratorError = undefined;

    try {
      for (var _iterator = target.elements[Symbol.iterator](), _step; !(_iteratorNormalCompletion = (_step = _iterator.next()).done); _iteratorNormalCompletion = true) {
        var field = _step.value;

        if (!field.hasAttribute("name")) {
          continue;
        }
        var fieldType = field.nodeName.toUpperCase() === "INPUT" && field.hasAttribute("type") ? field.getAttribute("type").toUpperCase() : "TEXT";
        if (fieldType === "FILE" && field.files.length > 0) {
          if (this.technique === 3) {
            // enctype is multipart/form-data
            var _iteratorNormalCompletion2 = true;
            var _didIteratorError2 = false;
            var _iteratorError2 = undefined;

            try {
              for (var _iterator2 = field.files[Symbol.iterator](), _step2; !(_iteratorNormalCompletion2 = (_step2 = _iterator2.next()).done); _iteratorNormalCompletion2 = true) {
                var file = _step2.value;

                var segmReq = new FileReader();

                // Custom properties:
                segmReq.segmentIdx = this.segments.length;
                segmReq.owner = this;

                segmReq.onload = pushSegment;
                this.segments.push("Content-Disposition: form-data; name=\"" + field.name + "\"; filename=\"" + file.name + "\"\r\nContent-Type: " + file.type + "\r\n\r\n");
                this.status++;
                segmReq.readAsBinaryString(file);
              }
            } catch (err) {
              _didIteratorError2 = true;
              _iteratorError2 = err;
            } finally {
              try {
                if (!_iteratorNormalCompletion2 && _iterator2.return) {
                  _iterator2.return();
                }
              } finally {
                if (_didIteratorError2) {
                  throw _iteratorError2;
                }
              }
            }
          } else {
            // enctype is application/x-www-form-urlencoded or text/plain or
            // method is GET: files will not be sent!
            var _iteratorNormalCompletion3 = true;
            var _didIteratorError3 = false;
            var _iteratorError3 = undefined;

            try {
              for (var _iterator3 = field.files[Symbol.iterator](), _step3; !(_iteratorNormalCompletion3 = (_step3 = _iterator3.next()).done); _iteratorNormalCompletion3 = true) {
                var _file = _step3.value;

                this.segments.push(filter(field.name) + "=" + filter(_file.name));
              }
            } catch (err) {
              _didIteratorError3 = true;
              _iteratorError3 = err;
            } finally {
              try {
                if (!_iteratorNormalCompletion3 && _iterator3.return) {
                  _iterator3.return();
                }
              } finally {
                if (_didIteratorError3) {
                  throw _iteratorError3;
                }
              }
            }
          }
        } else if (fieldType !== "RADIO" && fieldType !== "CHECKBOX" || field.checked) {
          // NOTE: this will submit _all_ submit buttons. Detecting the correct one is non-trivial.
          // field type is not FILE or is FILE but is empty.
          if (this.technique === 3) {
            // enctype is multipart/form-data
            this.segments.push("Content-Disposition: form-data; name=\"" + field.name + "\"\r\n\r\n" + field.value + "\r\n");
          } else {
            // enctype is application/x-www-form-urlencoded or text/plain or method is GET
            this.segments.push(filter(field.name) + "=" + filter(field.value));
          }
        }
      }
    } catch (err) {
      _didIteratorError = true;
      _iteratorError = err;
    } finally {
      try {
        if (!_iteratorNormalCompletion && _iterator.return) {
          _iterator.return();
        }
      } finally {
        if (_didIteratorError) {
          throw _iteratorError;
        }
      }
    }

    processStatus(this, xhrSuccess);
  }

  return function (formElement, xhrSuccess) {
    if (!formElement.action) {
      return;
    }
    new SubmitRequest(formElement, xhrSuccess);
  };
}();
