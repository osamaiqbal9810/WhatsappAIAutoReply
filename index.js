const express = require('express');
const bodyParser = require('body-parser');
const axios = require('axios');
const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');
const { MongoClient } = require('mongodb');

const app = express();
app.use(bodyParser.json());

// MongoDB Connection
const MONGODB_URI = process.env.MONGODB_URI || 'mongodb+srv://osamaiqbalcs:KAWj4pCIivlzy8vr@cluster0.gxnc4pq.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0';
const DB_NAME = 'whatsapp_bot';
let db;

async function connectToMongoDB() {
    try {
        const client = new MongoClient(MONGODB_URI);
        await client.connect();
        db = client.db(DB_NAME);
        console.log('Connected to MongoDB');
    } catch (error) {
        console.error('Failed to connect to MongoDB:', error);
        process.exit(1); // Exit if MongoDB connection fails
    }
}

// Call connectToMongoDB when the application starts
connectToMongoDB();

async function saveChatHistory(chatRecord) {
    try {
        const collection = db.collection('chatHistory');
        await collection.insertOne(chatRecord);
        console.log('Chat history saved to MongoDB.');
    } catch (error) {
        console.error('Failed to save chat history:', error);
    }
}

async function getChatHistory(userId, messageId, limit = 5) {
    try {
        const collection = db.collection('chatHistory');

        // Find the current message to get its timestamp
        let currentMessage = await collection.findOne({
            userId: userId,
            whatsappMessageId: messageId
        });

        if (!currentMessage) {
            console.log("!currentMessage")
            currentMessage = await collection.findOne({
                userId: userId,
                whatsappReplyMessageId: messageId
            });
        }
         if (!currentMessage) {
            return []
        }

        // Get 5 previous messages (before current)
        const previousMessages = await collection.find({
            userId: userId,
            timestamp: { $lt: currentMessage.timestamp }
        }).sort({ timestamp: -1 }).limit(limit).toArray();

        // Get 5 next messages (after current)
        const nextMessages = await collection.find({
            userId: userId,
            timestamp: { $gt: currentMessage.timestamp }
        }).sort({ timestamp: 1 }).limit(limit).toArray();

        // Combine and return 10 messages (without current)
        return previousMessages.reverse().concat(nextMessages);
    } catch (error) {
        console.error('Failed to retrieve chat history:', error);
        return [];
    }
}

async function getLatestMessagesExcludingList(userId, excludedIds, limit = 25) {
    try {
        const collection = db.collection('chatHistory');

        const latestMessages = await collection.find({
            userId: userId,
            _id: { $nin: excludedIds }
        }).sort({ timestamp: -1 }).limit(limit).toArray();

        return latestMessages;
    } catch (error) {
        console.error('Failed to retrieve latest messages:', error);
        return [];
    }
}



// --- To be updated with your Meta App credentials ---
const WHATSAPP_TOKEN = process.env.WHATSAPP_TOKEN || 'EAASMkHTUzx0BPKoNaRKn4avXAFxc2BsXpedkEckZAoIMDqTMS5S9Cz3ZAFHWZCcZA0lfc7lnsNMrJRBYMQaxwpeLIOD607tTzuzWYY91QqQUpu1ghAndbsftqHiH05Q4UwQnGVjoG2ZCC3ew7y82Fjti1FCV9GZA2pPZAumlMZBfd2Xk5PMMjDkTYMmK0Xd8rlGcdwZDZD';
const VERIFY_TOKEN = process.env.VERIFY_TOKEN || 'YOUR_VERIFY_TOKEN'; // This is a token you create
const PHONE_NUMBER_ID = process.env.PHONE_NUMBER_ID || '702753996254604';
const GEMINI_API_KEY = process.env.GEMINI_API_KEY || 'AIzaSyDls9FWqnviqujmcIdO5UTZmNpxrbTOf0k';

const PORT = process.env.PORT || 3000;

// Endpoint for WhatsApp to verify your webhook
app.get('/webhook', (req, res) => {
    const mode = req.query['hub.mode'];
    const token = req.query['hub.verify_token'];
    const challenge = req.query['hub.challenge'];

    if (mode && token) {
        if (mode === 'subscribe' && token === VERIFY_TOKEN) {
            console.log('WEBHOOK_VERIFIED');
            res.status(200).send(challenge);
        } else {
            res.sendStatus(403);
        }
    }
});

// Function to send a text message
async function sendTextMessage(to, text) {
    try {
        const response = await axios.post(`https://graph.facebook.com/v20.0/${PHONE_NUMBER_ID}/messages`, {
            messaging_product: 'whatsapp',
            to: to,
            text: { body: text }
        }, {
            headers: {
                'Authorization': `Bearer ${WHATSAPP_TOKEN}`,
                'Content-Type': 'application/json'
            }
        });
        console.log('Text reply sent successfully.' ,response.data.messages);
        return response.data.messages[0].id; // Return the message ID
    } catch (error) {
        console.error('Failed to send text reply:', error.response ? error.response.data : error.message);
        return null;
    }
}

// Function to send an audio message (placeholder for now)
async function sendAudioMessage(to, audioFilePath) {
    try {
        // 1. Upload the audio file to WhatsApp's media API
        const FormData = require('form-data');
        const form = new FormData();
        form.append('file', fs.createReadStream(audioFilePath));
        form.append('type', 'audio/mp3'); // Adjust content type if your TTS generates a different format
        form.append('messaging_product', 'whatsapp');

        const uploadResponse = await axios.post(`https://graph.facebook.com/v20.0/${PHONE_NUMBER_ID}/media`, form, {
            headers: {
                ...form.getHeaders(),
                'Authorization': `Bearer ${WHATSAPP_TOKEN}`,
            },
        });

        const mediaId = uploadResponse.data.id;
        console.log(`Audio uploaded to WhatsApp, media ID: ${mediaId}`);

        // 2. Send a message with the media ID
        const messageResponse = await axios.post(`https://graph.facebook.com/v20.0/${PHONE_NUMBER_ID}/messages`, {
            messaging_product: 'whatsapp',
            to: to,
            type: 'audio',
            audio: { id: mediaId }
        }, {
            headers: {
                'Authorization': `Bearer ${WHATSAPP_TOKEN}`,
                'Content-Type': 'application/json'
            }
        });
        console.log('Audio reply sent successfully.');
        return messageResponse.data.messages[0].id; // Return the message ID
    } catch (error) {
        console.error('Failed to send audio reply:', error.response ? error.response.data : error.message);
        return null;
    }
}

// Endpoint to handle incoming messages
app.post('/webhook', async (req, res) => {
    // console.log('Received webhook:', JSON.stringify(req.body, null, 2));
    const entry = req.body.entry;
    if (entry && entry[0].changes && entry[0].changes[0].value.messages) {
        const message = entry[0].changes[0].value.messages[0];
        const from = message.from; // User's phone number
        let queryText = "";

        if (message.type === 'text') {
            queryText = message.text.body;
            console.log(`Text message from ${from}: ${queryText}`);
        } else if (message.type === 'audio') {
            const audioId = message.audio.id;
            console.log(`Audio message from ${from}, audio ID: ${audioId}`);

            try {
                // 1. Get audio URL from WhatsApp
                const mediaUrlResponse = await axios.get(`https://graph.facebook.com/v20.0/${audioId}`, {
                    headers: {
                        'Authorization': `Bearer ${WHATSAPP_TOKEN}`
                    }
                });
                const audioUrl = mediaUrlResponse.data.url;
                console.log(`Audio URL: ${audioUrl}`);

                // 2. Download audio file
                const audioResponse = await axios({
                    method: 'get',
                    url: audioUrl,
                    responseType: 'stream',
                    headers: {
                        'Authorization': `Bearer ${WHATSAPP_TOKEN}`
                    }
                });

                const tempAudioPath = path.join(__dirname, 'temp_audio_' + audioId + '.ogg'); // Assuming .ogg based on WhatsApp docs
                const writer = fs.createWriteStream(tempAudioPath);
                audioResponse.data.pipe(writer);

                await new Promise((resolve, reject) => {
                    writer.on('finish', resolve);
                    writer.on('error', reject);
                });
                console.log(`Audio downloaded to: ${tempAudioPath}`);

                // 3. Transcribe audio
                const transcribeProcess = spawn('python', [path.join(__dirname, 'src/p4_transcribe_audio.py'), tempAudioPath]);
                let transcribedText = '';
                transcribeProcess.stdout.on('data', (data) => {
                    transcribedText += data.toString().trim();
                });
                transcribeProcess.stderr.on('data', (data) => {
                    console.error(`Transcribe script error: ${data}`);
                });

                await new Promise((resolve, reject) => {
                    transcribeProcess.on('close', (code) => {
                        if (code !== 0) {
                            console.error(`Transcribe script exited with code ${code}`);
                            reject(new Error(`Transcribe script failed with code ${code}`));
                        } else {
                            resolve();
                        }
                    });
                });
                queryText = transcribedText;
                console.log(`Transcribed text: ${queryText}`);

                // Clean up temporary audio file
                fs.unlink(tempAudioPath, (err) => {
                    if (err) console.error(`Error deleting temp audio file: ${err}`);
                    else console.log(`Deleted temp audio file: ${tempAudioPath}`);
                });

            } catch (error) {
                console.error('Error processing audio message:', error);
                await sendTextMessage(from, "Sorry, I had trouble processing your audio message.");
                res.sendStatus(200);
                return;
            }
        } else {
            console.log(`Received unsupported message type: ${message.type}`);
            await sendTextMessage(from, "Sorry, I can only process text and audio messages.");
            res.sendStatus(200);
            return;
        }

        if (!queryText) {
            console.log('No query text to process.');
            res.sendStatus(200);
            return;
        }

        // --- AI Logic using Milvus ---
        let chatHistoryContextMessages = []
        let chatHistoryContextSummary = "";
        let recent_chat_history = [];
        const whatsappUserId = from;
        const whatsappMessageId = message.id;
        const userId = message.context && message.context.from ? message.context.from : whatsappUserId;
        console.log("message", JSON.stringify(message))
        if (message.context && message.context.id) {
            // This is a reply to an old message
            console.log(`Reply to message ID: ${message.context.id}`);
            chatHistoryContextMessages = await getChatHistory(userId, message.context.id, 5);
            console.log("chatHistoryContextMessages", chatHistoryContextMessages)
            const excludedIds = chatHistoryContextMessages.map(msg => msg._id);
            recent_chat_history = await getLatestMessagesExcludingList(userId, excludedIds, 25);

            let queryBasedSystemPrompt = SystemPromptForChatHistoryBasedOnQuery(recent_chat_history.map(chat => ({ question: chat.question, answer: chat.answer })), queryText, chatHistoryContextMessages)
            const generateSummary = await axios.post('http://127.0.0.1:11434/api/generate', {
                model: 'gemma3:1b',
                prompt: queryBasedSystemPrompt,
                stream: false,
            });
            chatHistoryContextSummary = generateSummary.data.response

            // const response = await openai.chat.completions.create({
            //     model: 'gpt-4o-mini', // or 'gpt-4o' / 'gpt-4-turbo' / 'gpt-3.5-turbo'
            //     messages: [
            //         { role: 'system', content: queryBasedSystemPrompt },
            //     ],
            //     temperature: 0.1,
            //     stream: false,
            // });

            // const summaryDataBasedOnQuery = response.choices[0].message.content;

            // const assistantReply = response.choices[0].message.content;
            // console.log("GPT Response:", assistantReply);
            // Extract IDs to exclude

        }

        const milvusProcess = spawn('python', [path.join(__dirname, 'src/query_milvus.py')]);

        const inputData = {
            user_id: userId,
            data: {
                query: queryText,
                num_of_reference: 50,
                model: {
                    modelId: "gemini-2.5-flash",
                    contextWindow: 32768,
                    maxCompletionTokens: 8192
                },
                api_key: GEMINI_API_KEY,
                chat_history: chatHistoryContextSummary,
                recent_chat_history: formattedLastNChatQA(recent_chat_history.map(chat => ({ question: chat.question, answer: chat.answer })), chatHistoryContextMessages)
            }
        };

        milvusProcess.stdin.write(JSON.stringify(inputData));
        milvusProcess.stdin.end();

        let milvusOutput = '';
        milvusProcess.stdout.on('data', (data) => {
            milvusOutput += data.toString();
        });
        milvusProcess.stderr.on('data', (data) => {
            console.error(`Milvus query script error: ${data}`);
        });

        milvusProcess.on('close', async (code) => {
            if (code !== 0) {
                console.error(`Milvus query script exited with code ${code}`);
                await sendTextMessage(from, "Sorry, I encountered an error while processing your request.");
                return;
            }

            try {
                const jsonStart = milvusOutput.indexOf('{');
                if (jsonStart === -1) {
                    console.error('No JSON object found in Milvus script output.');
                    await sendTextMessage(from, "Sorry, I couldn't get a proper response.");
                    return;
                }
                const jsonString = milvusOutput.substring(jsonStart);
                const result = JSON.parse(jsonString);
                const answer = result.answer || "Sorry, I couldn't find an answer.";
                const whatsappUserId = from;
                const whatsappMessageId = message.id;
                const userId = message.context && message.context.from ? message.context.from : whatsappUserId;
                const references = result.references || [];
                let whatsappReplyMessageId = null;

                const chatRecord = {
                    _id: new Date().getTime(),
                    userId: userId,
                    question: queryText,
                    answer: answer,
                    model: "gemini-2.5-flash",
                    references: references,
                    whatsappUserId: whatsappUserId,
                    whatsappMessageId: whatsappMessageId,
                    whatsappReplyMessageId: whatsappReplyMessageId,
                    timestamp: new Date()
                };
               // await saveChatHistory(chatRecord);

                // If the original message was audio, convert the answer to speech and send audio
                if (message.type === 'audio') {
                    const outputAudioFilename = path.join(__dirname, 'output_audio_' + Date.now() + '.mp3');
                    const ttsProcess = spawn('python', [path.join(__dirname, 'src/p5_textToSpeech_audio.py'), answer, outputAudioFilename]);
                    let ttsOutput = '';
                    ttsProcess.stdout.on('data', (data) => {
                        ttsOutput += data.toString().trim();
                    });
                    ttsProcess.stderr.on('data', (data) => {
                        console.error(`TTS script error: ${data}`);
                    });

                    ttsProcess.on('close', async (ttsCode) => {
                        if (ttsCode !== 0) {
                            console.error(`TTS script exited with code ${ttsCode}`);
                            await sendTextMessage(from, "Sorry, I couldn't convert the answer to audio.");
                        } else {
                            console.log(`TTS output file: ${ttsOutput}`);
                            whatsappReplyMessageId = await sendAudioMessage(from, ttsOutput); // Call the placeholder function
                            chatRecord.whatsappReplyMessageId = whatsappReplyMessageId;
                            await saveChatHistory(chatRecord);
                            // Clean up generated audio file
                            fs.unlink(outputAudioFilename, (err) => {
                                if (err) console.error(`Error deleting generated audio file: ${err}`);
                                else console.log(`Deleted generated audio file: ${outputAudioFilename}`);
                            });
                        }
                    });
                } else {
                    // Otherwise, send text message
                    whatsappReplyMessageId = await sendTextMessage(from, answer);
                    chatRecord.whatsappReplyMessageId = whatsappReplyMessageId;
                    await saveChatHistory(chatRecord);
                }

            } catch (error) {
                console.error('Failed to process Milvus response or send reply:', error.response ? error.response.data : error.message);
                await sendTextMessage(from, "An unexpected error occurred.");
            }
        });
    }
    res.sendStatus(200);
});

app.listen(PORT, () => {
    console.log(`Server is listening on port ${PORT}`);
});


function SystemPromptForChatHistoryBasedOnQuery(
    chatHistories,
    query,
    contextMessages = []
) {
    const basePrompt = `You are an expert at distilling conversation history. Your task is to summarize the most relevant topic from the following recent chat history, specifically in the context of the user's latest question.

    Focus only on the information directly related to the user's current query and ignore irrelevant details. The summary should be concise and contain key entities or concepts that would be useful for searching a knowledge base.

    ---

    `;

    // ✅ Format context messages properly
    const formattedContextMessages = contextMessages.map(msg => {
        return `User: ${msg.question || msg.text || '[No Question]'}\nSystem: ${msg.answer || '[No Answer]'}`;
    }).join('\n');

    const additionalContextMsgs = formattedContextMessages
        ? `\n\nFollowing are the additional messages around replied message:\n${formattedContextMessages}`
        : '';

    const formattedChatHistories = chatHistories.length > 0
        ? `Recent Chat History:\nRelevant excerpts from recent conversation:\n` +
        chatHistories
            .map(chat => `User: ${chat.question || '[No Question]'}\nSystem: ${chat.answer || '[No Answer]'}`)
            .join('\n')
        : '';

    const usersLatestQuestion = `\n\n---\nUser's Latest Question:\n${query}\n---`;
    //  console.log("${basePrompt}${additionalContextMsgs}${formattedChatHistories}${usersLatestQuestion}\n"+ `${basePrompt}${additionalContextMsgs}${formattedChatHistories}${usersLatestQuestion}`)
    return `${basePrompt}${formattedChatHistories}${additionalContextMsgs}${usersLatestQuestion}`;
}


function formattedLastNChatQA(chatHistories, contextMessages = []) {
    const formattedContextMessages = contextMessages.length > 0
        ? contextMessages.map(msg => {
            return `User: ${msg.question || msg.text || '[No Question]'}\nSystem: ${msg.answer || '[No Answer]'}`;
        }).join('\n')
        : '';

    const additionalContextMsgs = formattedContextMessages
        ? `\n\nFollowing are the additional messages around replied message:\n${formattedContextMessages}`
        : '';

    const formattedChatHistories =
        `Following are messages from recent conversation:\n` +
        chatHistories
            .map((chat) => {
                return `User: ${chat.question || '[No Question]'}\nSystem: ${chat.answer || '[No Answer]'}`;
            })
            .join('\n');
    // console.log("${additionalContextMsgs}${formattedChatHistories}\n", `${additionalContextMsgs}${formattedChatHistories}`)
    return `${additionalContextMsgs}${formattedChatHistories}`;
}
