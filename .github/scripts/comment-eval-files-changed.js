module.exports = async ({ github, context }) => {
  const changedFiles = process.env.CHANGED_FILES || "See file diff above";
  const hasOpenAI = process.env.HAS_OPENAI_KEY === "true";

  const body = `## 🧪 Evaluation Files Updated

This PR includes changes to evaluation files. The MCP evaluations will run automatically.

**OpenAI Integration**: ${hasOpenAI ? "✅ Available" : "⚠️ Not configured - manual tests only"}

**Tip**: Add the \`comprehensive-eval\` label to run the full evaluation suite.

### Modified evaluation files:
${changedFiles}

${hasOpenAI ? "" : "\n**Note**: To run full AI-powered evaluations, configure the `OPENAI_API_KEY` repository secret."}
`;

  await github.rest.issues.createComment({
    issue_number: context.issue.number,
    owner: context.repo.owner,
    repo: context.repo.repo,
    body: body,
  });
};
