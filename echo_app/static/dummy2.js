async function test() {
  var xhr;
  if (!(typeof XMLHttpRequest == 'undefined')) {
    xhr = new XMLHttpRequest();
  } else {
    xhr = new ActiveXObject("Microsoft.XMLHTTP")
  }
  xhr.open("POST", '#abc');
  var result = await new Promise(function (resolve, reject) {
    var xhr1;
    if (!(typeof XMLHttpRequest == 'undefined')) {
      xhr1 = new XMLHttpRequest();
    } else {
      xhr1 = new ActiveXObject("Microsoft.XMLHTTP")
    }
    xhr1.open("POST", '#bcd');
    xhr1.send('hello2');
  });
  xhr.send('hello1');
}
test();