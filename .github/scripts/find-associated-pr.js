module.exports = async ({ github, context }) => {
  const branch = process.env.TARGET_BRANCH;

  if (branch === "main") {
    return null;
  }

  const { data: pulls } = await github.rest.pulls.list({
    owner: context.repo.owner,
    repo: context.repo.repo,
    head: `${context.repo.owner}:${branch}`,
    state: "open",
  });

  return pulls.length > 0 ? pulls[0].number : null;
};
