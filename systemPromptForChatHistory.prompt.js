export function SystemPromptForChatHistoryBasedOnQuery(
  chatHistories,
  query,
  contextMessages = []
) {
  const basePrompt = `You are an expert at distilling conversation history. Your task is to summarize the most relevant topic from the following recent chat history, specifically in the context of the user's latest question.

Focus only on the information directly related to the user's current query and ignore irrelevant details. The summary should be concise and contain key entities or concepts that would be useful for searching a knowledge base.

---

Recent Chat History:
`;
  // Format chatHistories
  const chatHistoryIds = new Set(chatHistories.map(chat => chat.whatsappMessageId));
  const nonOverlappingContextMessages = contextMessages
    .filter(ctx => !chatHistoryIds.has(ctx.whatsappMessageId))
    .map(ctx => ctx.text);

  const additionalContextMsgs = nonOverlappingContextMessages.length > 0
    ? `\n\nFollowing are the additional messages around replied message:\n${nonOverlappingContextMessages.join('\n')}`
    : '';

  const formattedChatHistories =
    chatHistories.length > 0
      ?
      `Relevant excerpts from recent conversation:\n` +
      chatHistories
        .map((chat) => `User: ${chat.question}\nSystem: ${chat.answer}`)
        .join('\n')
      : '';


  const usersLatestQuestion = `\n\n---\nUser's Latest Question:\n${query}\n---`;
  return `${basePrompt}${additionalContextMsgs}${formattedChatHistories}${usersLatestQuestion}`;
}



export function formattedLastNChatQA(chatHistories, contextMessages = []) {
  const chatHistoryIds = new Set(chatHistories.map(chat => chat.whatsappMessageId));
  const nonOverlappingContextMessages = contextMessages
    .filter(ctx => !chatHistoryIds.has(ctx.whatsappMessageId))
    .map(ctx => ctx.text);

  const additionalContextMsgs = nonOverlappingContextMessages.length > 0
    ? `\n\nFollowing are the additional messages around replied message:\n${nonOverlappingContextMessages.join('\n')}`
    : '';
  const formattedChatHistories =
    `Following are messages from recent conversation:\n` +
    chatHistories
      .map((chat) => {

        return `User: ${chat.question}\n System: ${chat.answer}`;
      })
      .join('\n');
  return `${additionalContextMsgs}${formattedChatHistories}`;
}