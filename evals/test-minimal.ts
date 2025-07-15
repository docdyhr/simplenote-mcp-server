import { openai } from "@ai-sdk/openai";
import { EvalConfig, EvalFunction, grade } from 'mcp-evals';

const serverHealthCheck: EvalFunction = {
    name: 'server_health_check',
    description: 'Basic server health and responsiveness test',
    run: async (model) => {
        try {
            // For now, just return a basic response since we don't have real server integration
            const result = await grade(model, "Check if the Simplenote MCP server is running and can respond to basic requests");
            return JSON.parse(result);
        } catch (error) {
            return {
                accuracy: 1,
                completeness: 1,
                relevance: 1,
                clarity: 1,
                reasoning: 1,
                overall_comments: `Error during evaluation: ${error instanceof Error ? error.message : String(error)}`
            };
        }
    }
};

const config: EvalConfig = {
    model: openai("gpt-4o-mini"),
    evals: [serverHealthCheck]
};

export default config;
