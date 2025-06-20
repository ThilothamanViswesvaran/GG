// Add this to your existing JavaScript
document.addEventListener('DOMContentLoaded', function () {
  // Prevent event interference with text selection
  const initialMessage = document.querySelector('.chatbot-body .bot-message');
    if (initialMessage) {
        initialMessage.textContent = initialMessage.textContent.trim();
    }
  document.querySelectorAll('.chat-message').forEach(msg => {
    msg.style.userSelect = 'text';
    msg.style.webkitUserSelect = 'text';
  });
  // Make sure new messages are selectable
  const observer = new MutationObserver(function (mutations) {
    mutations.forEach(function (mutation) {
      mutation.addedNodes.forEach(function (node) {
        if (node.classList && node.classList.contains('chat-message')) {
          node.style.userSelect = 'text';
          node.style.webkitUserSelect = 'text';
          node.style.cursor = 'text';
        }
      });
    });
  });

  observer.observe(document.getElementById('chatbotBody'), {
    childList: true,
    subtree: true
  });
});

// Track if chatbot has been initialized
let chatbotInitialized = false;

// Toggle chatbot visibility
function toggleChatbot() {
  const chatbot = document.getElementById('chatbotContainer');
  chatbot.classList.toggle('visible');

  // Initialize chatbot only once
  if (!chatbotInitialized && chatbot.classList.contains('visible')) {
    initializeChatbot();
    chatbotInitialized = true;
  }
}

function displayMessage(message, isUser = false) {
    const chatbotBody = document.getElementById('chatbotBody');
    const messageDiv = document.createElement('div');
    messageDiv.className = isUser ? 'chat-message user-message' : 'chat-message bot-message';
    
    // Convert to HTML with proper paragraph breaks only between bullet points
    let formattedMessage = message;
    if (message.includes('•')) {
        // Split by bullet points
        const points = message.split('•').filter(p => p.trim());
        
        // Create paragraphs for each point
        formattedMessage = points.map(p => {
            // Remove any existing newlines within the point
            const cleanPoint = p.replace(/\n/g, ' ').trim();
            return `<p class="bullet-point">• ${cleanPoint}</p>`;
        }).join('');
    } else {
        // Regular message without bullets
        formattedMessage = `<p>${message}</p>`;
    }
    
    messageDiv.innerHTML = formattedMessage;
    chatbotBody.appendChild(messageDiv);
    chatbotBody.scrollTop = chatbotBody.scrollHeight;
}

// Initialize chatbot with welcome message
function initializeChatbot() {
  const chatBody = document.getElementById('chatbotBody');

  if (!document.querySelector('.chat-message.bot-message')) {
    const welcomeMessage = createSelectableMessage(
      "Hello! I'm your university assistant. How can I help you today?",
      false
    );
    chatBody.insertBefore(welcomeMessage, chatBody.firstChild);
  }
}

// Send quick link message
function sendQuickLink(message) {
  const chatbotInput = document.getElementById('chatbotInput');
  chatbotInput.value = message;
  sendChatbotMessage();
}

// Create typing indicator
function createTypingIndicator() {
  const typingDiv = document.createElement('div');
  typingDiv.className = 'chat-message bot-message typing-indicator';
  typingDiv.id = 'typingIndicator';

  for (let i = 0; i < 3; i++) {
    const dot = document.createElement('div');
    dot.className = 'typing-dot';
    typingDiv.appendChild(dot);
  }

  return typingDiv;
}

// Send message to backend
async function sendChatbotMessage() {
  const input = document.getElementById('chatbotInput');
  const message = input.value.trim();
  if (!message) return;

  const chatBody = document.getElementById('chatbotBody');

  // In your sendChatbotMessage function, update the message creation:
  const userMessage = createSelectableMessage(message, true);
  chatBody.appendChild(userMessage);

  function createSelectableMessage(content, isUser) {
    const message = document.createElement('div');
    message.className = isUser ? 'chat-message user-message' : 'chat-message bot-message';
    message.textContent = content;

    // Force text selection capabilities
    message.style.userSelect = 'text';
    message.style.webkitUserSelect = 'text';
    message.style.mozUserSelect = 'text';
    message.style.msUserSelect = 'text';
    message.style.cursor = 'text';

    return message;
  }

  input.value = '';
  chatBody.scrollTop = chatBody.scrollHeight;

  // Show typing indicator
  const typingIndicator = createTypingIndicator();
  chatBody.appendChild(typingIndicator);
  chatBody.scrollTop = chatBody.scrollHeight;

  try {
    // Get response from backend
    const botResponse = await getBotResponse(message);

    // Remove typing indicator
    chatBody.removeChild(typingIndicator);

    // And for bot messages:
    const botMessage = document.createElement('div');
    botMessage.className = 'chat-message bot-message';
    botMessage.textContent = botResponse;
    chatBody.appendChild(botMessage);
  } catch (error) {
    // Remove typing indicator on error
    chatBody.removeChild(typingIndicator);

    // Show error message
    const errorMessage = document.createElement('div');
    errorMessage.className = 'chat-message bot-message';
    errorMessage.textContent = "I'm having trouble connecting to the knowledge base. Please try again later.";
    chatBody.appendChild(errorMessage);

    console.error("Error:", error);
  }

  chatBody.scrollTop = chatBody.scrollHeight;
}

// Call backend API
async function getBotResponse(message) {
  try {
    const response = await fetch('http://localhost:8000/ask', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        question: message
      })
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    return data.answer || "I couldn't find an answer to that question.";

  } catch (error) {
    console.error("API Error:", error);
    throw error;
  }
}

function addMessageToChat(text, isUser) {
  const messageDiv = document.createElement('div');
  messageDiv.className = isUser ? 'chat-message user-message' : 'chat-message bot-message';
  
  // Use innerHTML only if you trust the source (sanitize if from user input)
  messageDiv.innerHTML = text;
  
  // Make links both clickable and selectable
  messageDiv.querySelectorAll('a').forEach(link => {
    link.style.pointerEvents = 'auto';
    link.style.cursor = 'text';
  });
  
  document.getElementById('chatbotBody').appendChild(messageDiv);
}

function addMessage(message, isUser = false) {
    const chatBody = document.getElementById('chatbotBody');
    const messageDiv = document.createElement('div');
    messageDiv.className = isUser ? 'chat-message user-message' : 'chat-message bot-message';
    
    // Create container for message and copy button
    const container = document.createElement('div');
    container.className = 'copy-btn-container';
    
    // Add the message content
    const content = document.createElement('div');
    content.innerHTML = formatMessage(message);
    container.appendChild(content);
    
    // Add copy button
    const copyBtn = document.createElement('button');
    copyBtn.className = 'copy-btn';
    copyBtn.textContent = 'Copy';
    copyBtn.onclick = () => {
        navigator.clipboard.writeText(messageDiv.textContent);
        copyBtn.textContent = 'Copied!';
        setTimeout(() => copyBtn.textContent = 'Copy', 2000);
    };
    container.appendChild(copyBtn);
    
    messageDiv.appendChild(container);
    chatBody.appendChild(messageDiv);
    chatBody.scrollTop = chatBody.scrollHeight;
}

function formatMessage(message) {
    // Convert bullet points and line breaks
    return message
        .replace(/•/g, '<span class="bullet">•</span>')
        .replace(/\n/g, '<br>');
}

// Auto-focus input when chatbot opens
document.getElementById('chatbotContainer').addEventListener('transitionend', function () {
  if (this.classList.contains('visible')) {
    document.getElementById('chatbotInput').focus();
  }
});
