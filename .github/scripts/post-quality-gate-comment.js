module.exports = async ({ github, context, core }) => {
  const fs = require("fs");

  try {
    const report = fs.readFileSync("quality-gate-report.md", "utf8");

    const comments = await github.rest.issues.listComments({
      owner: context.repo.owner,
      repo: context.repo.repo,
      issue_number: context.issue.number,
    });

    const existingComment = comments.data.find((comment) =>
      comment.body.includes("Evaluation Quality Gate Report"),
    );

    if (existingComment) {
      await github.rest.issues.updateComment({
        owner: context.repo.owner,
        repo: context.repo.repo,
        comment_id: existingComment.id,
        body: report,
      });
      console.log("Updated existing quality gate comment");
    } else {
      await github.rest.issues.createComment({
        owner: context.repo.owner,
        repo: context.repo.repo,
        issue_number: context.issue.number,
        body: report,
      });
      console.log("Created new quality gate comment");
    }
  } catch (error) {
    console.error("Failed to post quality gate comment:", error);
    core.setFailed(`Failed to post comment: ${error.message}`);
  }
};
