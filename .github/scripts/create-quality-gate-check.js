module.exports = async ({ github, context }) => {
  const passRate = process.env.PASS_RATE;
  const qualityGatePassed = process.env.QUALITY_GATE_PASSED === "true";
  const evalResult = process.env.EVAL_RESULT;

  let conclusion, title, summary;

  if (evalResult === "success" && qualityGatePassed) {
    conclusion = "success";
    title = "✅ Quality Gate Passed";
    summary = `Evaluation pass rate: ${passRate}% (meets threshold)`;
  } else if (evalResult === "success") {
    conclusion = "neutral"; // Non-blocking
    title = "⚠️ Quality Gate Below Threshold";
    summary = `Evaluation pass rate: ${passRate}% (below threshold but non-blocking)`;
  } else {
    conclusion = "neutral"; // Non-blocking
    title = "❌ Evaluation Failed";
    summary = "Evaluations failed to complete successfully (non-blocking)";
  }

  await github.rest.checks.create({
    owner: context.repo.owner,
    repo: context.repo.repo,
    name: "Evaluation Quality Gate",
    head_sha: context.sha,
    conclusion: conclusion,
    output: {
      title: title,
      summary: summary,
      text: `
This is a non-blocking quality gate based on MCP evaluation results.

**Pass Rate**: ${passRate}%
**Threshold**: ${process.env.FAIL_THRESHOLD}%
**Suite**: ${process.env.EVALUATION_SUITE}

Check the evaluation artifacts for detailed results.
      `,
    },
  });
};
