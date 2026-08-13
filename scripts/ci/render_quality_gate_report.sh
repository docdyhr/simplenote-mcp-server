#!/bin/bash
# Render the evaluation quality-gate markdown report (quality-gate-report.md).
# Reads PASS_RATE, QUALITY_GATE_PASSED, STATUS, RUN_RESULT, FAIL_THRESHOLD,
# EVALUATION_SUITE from the environment; writes overall_status/report_created
# to $GITHUB_OUTPUT.

set -euo pipefail

echo "Creating quality gate report..."

if [ "$RUN_RESULT" = "success" ] && [ "$QUALITY_GATE_PASSED" = "true" ]; then
  OVERALL_STATUS="✅ PASSED"
  GATE_EMOJI="🟢"
elif [ "$RUN_RESULT" = "success" ] && [ "$QUALITY_GATE_PASSED" = "false" ]; then
  OVERALL_STATUS="⚠️ PASSED (Below Threshold)"
  GATE_EMOJI="🟡"
else
  OVERALL_STATUS="❌ FAILED"
  GATE_EMOJI="🔴"
fi

cat > quality-gate-report.md << EOF
# ${GATE_EMOJI} Evaluation Quality Gate Report

## Overall Result: ${OVERALL_STATUS}

**Pass Rate**: ${PASS_RATE}%
**Threshold**: ${FAIL_THRESHOLD}%
**Evaluation Suite**: ${EVALUATION_SUITE}
**Quality Gate**: ${QUALITY_GATE_PASSED}

## Assessment

EOF

case "$STATUS" in
  success)
    {
      echo "🎉 **Excellent!** All evaluations passed successfully."
      echo ""
      echo "The code changes maintain high quality standards and functionality."
    } >> quality-gate-report.md
    ;;
  good)
    {
      echo "✅ **Good!** Evaluations passed with high success rate."
      echo ""
      echo "The code changes meet quality standards with minor issues."
    } >> quality-gate-report.md
    ;;
  acceptable)
    {
      echo "⚠️ **Acceptable** but could be improved."
      echo ""
      echo "The code changes meet minimum quality requirements."
      echo "Consider reviewing failed tests and improving implementation."
    } >> quality-gate-report.md
    ;;
  poor)
    {
      echo "🔴 **Poor performance** - significant issues detected."
      echo ""
      echo "The code changes have quality issues that should be addressed."
      echo "Review failed evaluations and improve implementation before merging."
    } >> quality-gate-report.md
    ;;
  *)
    {
      echo "❓ **Unknown status** - evaluation results unclear."
      echo ""
      echo "Please review the evaluation logs for more information."
    } >> quality-gate-report.md
    ;;
esac

{
  echo ""
  echo "## Recommendations"
  echo ""
} >> quality-gate-report.md

if [ "$QUALITY_GATE_PASSED" = "false" ]; then
  {
    echo "- 🔍 **Review failed evaluations** in the uploaded artifacts"
    echo "- 🛠️ **Fix failing test scenarios** to improve pass rate"
    echo "- 📋 **Update implementation** based on evaluation feedback"
    echo "- ✅ **Re-run evaluations** after making improvements"
  } >> quality-gate-report.md
else
  {
    echo "- ✅ **Quality gate passed** - no immediate action required"
    echo "- 📊 **Monitor evaluation trends** over time"
    echo "- 🎯 **Consider running comprehensive evaluations** for important changes"
  } >> quality-gate-report.md
fi

{
  echo ""
  echo "---"
  echo "*Quality gate is currently non-blocking. This assessment is for informational purposes.*"
  echo ""
  echo "📁 **Evaluation artifacts**: Check the Actions tab for detailed results"
} >> quality-gate-report.md

echo "overall_status=${OVERALL_STATUS}" >> "$GITHUB_OUTPUT"
echo "report_created=true" >> "$GITHUB_OUTPUT"

cat quality-gate-report.md
