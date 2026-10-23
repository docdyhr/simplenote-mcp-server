module.exports = async ({ github, context }) => {
  const changedFiles = process.env.CHANGED_FILES || "See file diff above";

  const body = `## 🧪 Evaluation Files Updated

This PR includes changes to evaluation files. The **Evaluation Quality Gate** workflow runs the basic suite on it automatically. It skips the run when \`OPENAI_API_KEY\` isn't available (Dependabot and fork PRs).

**Tip**: To run the full suite, dispatch *Evaluation Quality Gate* from the Actions tab with \`evaluation_suite: comprehensive\`.

### Modified evaluation files:
${changedFiles}
`;

  await github.rest.issues.createComment({
    issue_number: context.issue.number,
    owner: context.repo.owner,
    repo: context.repo.repo,
    body: body,
  });
};
