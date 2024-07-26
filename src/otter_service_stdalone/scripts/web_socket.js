/**
 * This is main function of the script. It sets up the web sockets and handles messages
 * coming from the application. The last line of the script calls this function
 */
function connectWebSocket() {
    var loc = window.location;
    var wsStart = loc.protocol === "https:" ? "wss://" : "ws://";
    var wsUrl = wsStart + loc.host + "/update";

    var ws = new WebSocket(wsUrl);
    submission_divs = {}
    reconnectInterval = 3000;
    ws.onopen = function() {
        console.log("WebSocket is open now.");
        reconnectInterval = 3000;
    };

    ws.onmessage = function(event) {
        var messagesDiv = document.getElementById("messages");
        var noneMsgP = document.getElementById("none-msg");
        noneMsgP.style.display = "none"
        json_msgs = JSON.parse(event.data)["messages"];
        console.log(json_msgs)
        Object.entries(json_msgs).forEach(([submission_key, messages], index) => {
          var element = document.getElementById(submission_key);
          if (element==null){
            messagesDiv.appendChild(_setUpNewSubmission(submission_key, index, messages))
          } else {
            _updateSubmission(submission_key, index, messages)
          }
          
          messagesDiv.scrollTop = messagesDiv.scrollHeight;
        });
    };

    ws.onclose = function() {
        //if closes attempts re-connect every few seconds
        console.log("WebSocket is closed now.");
        setTimeout(connectWebSocket, 3000);
    };

    ws.onerror = function(error) {
        console.error('WebSocket error:', error);
        ws.close();
    };
  };

/**
 * This function sets up the div that will report progress on the given submission
 * in the application
 * @param {*} submission_key doanload code - unique to submission
 * @param {*} index - the submission number in this session for the user
 * @param {*} messages - all the messages that need to be added to progress
 */
function _setUpNewSubmission(submission_key, index, messages){
    var newMessage = document.createElement("div");
    newMessage.id = submission_key
    var newMessageHeader = document.createElement("div");
    var newMessageContent = document.createElement("div");
    newMessageContent.id = "msg-" + submission_key
    newMessageHeader.id = "header-" + submission_key
    var toggleSign =  document.createElement("span");
    var submissionHeader =  document.createElement("span");
    submissionHeader.innerHTML = " Submission Progress: Submission #" + (index+1)
    submissionHeader.id = "sub-header-" + submission_key
    newMessage.className = "collapsible"
    newMessageHeader.className = "header"
    toggleSign.innerHTML = '<i class="fas fa-minus-circle"></i>';
  
    newMessageHeader.appendChild(toggleSign)
    newMessageHeader.appendChild(submissionHeader)
    newMessageContent.className = "content"
    newMessageContent.style.display = "block"
    newMessage.appendChild(newMessageHeader)
    newMessage.appendChild(newMessageContent)
    submission_divs[submission_key] = newMessage
    const li = document.createElement('li');
    li.textContent = "Download Code: " + submission_key;
    newMessageContent.appendChild(li);
    for (const m of messages) {
      const li = document.createElement('li');
      li.textContent = m;
      newMessageContent.appendChild(li);
    }
    // Toggle the visibility of the scrollable content
    newMessageHeader.addEventListener('click', () => {
      if (newMessageContent.style.display == 'none') {
        newMessageContent.style.display = 'block';
        toggleSign.innerHTML = '<i class="fas fa-minus-circle"></i>';
      } else {
        newMessageContent.style.display = 'none';
        toggleSign.innerHTML = '<i class="fas fa-plus-circle"></i>';
      }
    });
    return newMessage;
}

/**
 * This updates the progress div for this submission
 * 
 * @param {*} submission_key doanload code - unique to submission
 * @param {*} index - the submission number in this session for the user
 * @param {*} messages - all the messages that need to be added to progress
 */
function _updateSubmission(submission_key, index, messages){
    var newMessageContent = document.getElementById("msg-" + submission_key);
    var items = newMessageContent.getElementsByTagName("li");
    var msgs = []
    for (var i = 0; i < items.length; ++i) {
        msgs.push(items[i].textContent)
    }
    for (const m of messages) {
      if(!(msgs.includes(m))){
        const li = document.createElement('li');
        li.textContent = m;
        newMessageContent.appendChild(li);
      }
    }
    if(messages.includes("Results available for download")){
      var header = document.getElementById("header-" + submission_key)
      header.style.backgroundColor = '#7BAE37';
      var subheader = document.getElementById("sub-header-" + submission_key)
      subheader.innerHTML = " Submission Progress: Submission #" + (index+1) + "</br>Download Code: " + submission_key;
      newMessageContent.style.display = 'none';
    }
}


connectWebSocket()
