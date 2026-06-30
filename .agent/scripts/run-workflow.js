const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { execSync } = require('child_process');

const PROJECT_ROOT = path.join(__dirname, '..', '..');
const WORKFLOWS_DIR = path.join(PROJECT_ROOT, '.agent', 'workflows');
const RUNS_DIR = path.join(PROJECT_ROOT, '.agent', 'runs');
const REGISTRY_FILE = path.join(PROJECT_ROOT, '.agent', 'registry.json');
const SCHEMAS_DIR = path.join(PROJECT_ROOT, '.agent', 'schemas');
const POLICIES_DIR = path.join(PROJECT_ROOT, '.agent', 'policies');

function generateRunId() {
    return 'run_' + crypto.randomBytes(4).toString('hex') + '_' + Date.now();
}

function checkPreconditions(preconditions) {
    for (const condition of preconditions) {
        if (condition === "registry_exists") {
            if (!fs.existsSync(REGISTRY_FILE)) return { passed: false, reason: "registry.json not found" };
        }
        if (condition === "schemas_valid") {
            if (!fs.existsSync(SCHEMAS_DIR)) return { passed: false, reason: "schemas directory not found" };
        }
    }
    return { passed: true };
}

class WorkflowRunner {
    constructor(workflowId, approvedRunId = null) {
        this.workflowId = workflowId;
        this.metaFile = path.join(WORKFLOWS_DIR, `${workflowId}.json`);
        
        if (!fs.existsSync(this.metaFile)) {
            console.error(`[Error] Workflow metadata not found for '${workflowId}'.`);
            process.exit(1);
        }
        this.metadata = JSON.parse(fs.readFileSync(this.metaFile, 'utf8'));

        if (approvedRunId) {
            this.runId = approvedRunId;
            this.runDir = path.join(RUNS_DIR, this.runId);
            if (!fs.existsSync(this.runDir)) {
                console.error(`[Error] Run directory not found for ID '${approvedRunId}'.`);
                process.exit(1);
            }
            this.report = JSON.parse(fs.readFileSync(path.join(this.runDir, 'report.json'), 'utf8'));
            this.logs = [];
            this.isResuming = true;
        } else {
            this.runId = generateRunId();
            this.runDir = path.join(RUNS_DIR, this.runId);
            fs.mkdirSync(this.runDir, { recursive: true });
            fs.mkdirSync(path.join(this.runDir, 'artifacts'), { recursive: true });
            
            this.report = {
                run_id: this.runId,
                workflow_id: this.workflowId,
                status: "created",
                started_at: new Date().toISOString(),
                ended_at: null,
                steps: []
            };
            this.logs = [];
            this.isResuming = false;
        }
    }

    logAndRecord(msg) {
        console.log(`[State: ${this.report.status}] ${msg}`);
        this.logs.push(`[${new Date().toISOString()}] ${msg}`);
    }

    saveReport() {
        fs.writeFileSync(path.join(this.runDir, 'report.json'), JSON.stringify(this.report, null, 2));
    }

    updateState(newState) {
        this.report.status = newState;
        this.saveReport();
    }

    async run() {
        if (!this.isResuming) {
            this.logAndRecord(`Starting Workflow: ${this.workflowId} (Run ID: ${this.runId})`);
            
            this.updateState("checking_preconditions");
            const checkResult = checkPreconditions(this.metadata.preconditions || []);
            if (!checkResult.passed) {
                this.updateState("blocked");
                this.logAndRecord(`Blocked. Precondition failed: ${checkResult.reason}`);
                process.exit(1);
            }
            this.logAndRecord(`Preconditions passed.`);

            this.updateState("enforcing_policy");
            const workflowGatesFile = path.join(POLICIES_DIR, 'workflow-gates.json');
            if (fs.existsSync(workflowGatesFile)) {
                const gates = JSON.parse(fs.readFileSync(workflowGatesFile, 'utf8'));
                for (const rule of gates.rules) {
                    if (rule.when && rule.when.risk && rule.when.risk.includes(this.metadata.risk)) {
                        this.logAndRecord(`Policy Match [${rule.id}]: Workflow risk is ${this.metadata.risk}.`);
                    }
                }
            }

            this.updateState("planning");
            this.logAndRecord(`Loading required agents: ${this.metadata.required_agents.join(', ')}`);
        } else {
            this.logAndRecord(`Resuming Workflow: ${this.workflowId} (Run ID: ${this.runId})`);
            this.updateState("running_step");
        }
        
        const steps = this.metadata.steps || [];
        
        for (const step of steps) {
            // Skip steps that are already completed
            const existingStep = this.report.steps.find(s => s.step_id === step.id);
            if (existingStep && existingStep.state === "completed") {
                continue;
            }

            this.updateState("running_step");
            this.logAndRecord(`Executing step: ${step.id} (Agent: ${step.agent})`);
            
            let stepRecord = existingStep;
            if (!stepRecord) {
                stepRecord = { step_id: step.id, agent: step.agent, state: "running" };
                this.report.steps.push(stepRecord);
            }

            // Approval Gate Check
            if (step.requires_approval) {
                if (existingStep && existingStep.approved) {
                    this.logAndRecord(`Step '${step.id}' was manually approved. Resuming execution.`);
                } else {
                    this.updateState("waiting_approval");
                    this.logAndRecord(`Step '${step.id}' requires manual approval. Halting workflow.`);
                    
                    fs.writeFileSync(path.join(this.runDir, 'approval_required.json'), JSON.stringify({
                        run_id: this.runId,
                        workflow_id: this.workflowId,
                        step_id: step.id,
                        action: step.action,
                        message: "Please review the plan/artifacts before approving. To resume, run with --approved <run-id>"
                    }, null, 2));

                    stepRecord.state = "waiting_approval";
                    this.saveReport();
                    this.generateWalkthrough();
                    process.exit(0);
                }
            }
            
            if (step.action === "run_validation") {
                this.updateState("validating");
                if (step.commands) {
                    for (const cmd of step.commands) {
                        this.logAndRecord(`Running validation command: ${cmd}`);
                        try {
                            execSync(cmd, { cwd: PROJECT_ROOT, stdio: 'ignore' });
                            this.logAndRecord(`Validation command passed: ${cmd}`);
                        } catch (e) {
                            this.logAndRecord(`Validation command failed: ${cmd}`);
                            stepRecord.state = "failed";
                            this.updateState("failed");
                            process.exit(1);
                        }
                    }
                }
            } else {
                this.logAndRecord(`[SIMULATOR/DRY-RUN] Action '${step.action}' execution mock started.`);
                // If it produces outputs, mock their creation for testing purposes (in reality the agent would create them)
                if (step.outputs) {
                    for (const out of step.outputs) {
                        fs.writeFileSync(path.join(this.runDir, 'artifacts', out), JSON.stringify({ content: "mock" }));
                    }
                }
                this.logAndRecord(`[SIMULATOR/DRY-RUN] Action '${step.action}' completed.`);
            }

            // Artifact Enforcement
            if (step.outputs && step.outputs.length > 0) {
                this.logAndRecord(`Enforcing artifacts for step '${step.id}'...`);
                for (const expectedOut of step.outputs) {
                    const artifactPath = path.join(this.runDir, 'artifacts', expectedOut);
                    if (!fs.existsSync(artifactPath)) {
                        this.logAndRecord(`[Artifact Error] Required output '${expectedOut}' not found in artifacts/`);
                        stepRecord.state = "failed";
                        this.updateState("failed");
                        process.exit(1);
                    }
                }
                this.logAndRecord(`Artifact enforcement passed.`);
            }

            stepRecord.state = "completed";
            this.saveReport();
        }

        this.logAndRecord(`All steps completed. Checking completion gates...`);
        if (this.metadata.memory_policy === "sync_after_validation") {
            this.updateState("synced_memory");
            this.logAndRecord(`Memory synced successfully.`);
        }

        this.report.ended_at = new Date().toISOString();
        this.updateState("completed");
        this.logAndRecord(`Workflow completed successfully.`);

        this.generateWalkthrough();
    }

    generateWalkthrough() {
        const md = `# [SIMULATOR/DRY-RUN] Run Report: ${this.workflowId}\n\n` +
                   `- **Run ID:** \`${this.runId}\`\n` +
                   `- **Status:** ${this.report.status.toUpperCase()}\n` +
                   `- **Start:** ${this.report.started_at}\n` +
                   `- **End:** ${this.report.ended_at || 'N/A'}\n\n` +
                   `## Logs\n\`\`\`\n${this.logs.join('\n')}\n\`\`\`\n`;
        fs.writeFileSync(path.join(this.runDir, 'walkthrough.md'), md);
    }
}

if (require.main === module) {
    const args = process.argv.slice(2);
    if (args.length === 0) {
        console.log("Usage: node run-workflow.js <workflow-id> [--approved <run-id>]");
        process.exit(1);
    }
    
    const workflowId = args[0];
    let approvedRunId = null;
    
    const approvedIndex = args.indexOf('--approved');
    if (approvedIndex !== -1 && args.length > approvedIndex + 1) {
        approvedRunId = args[approvedIndex + 1];
    }
    
    const runner = new WorkflowRunner(workflowId, approvedRunId);
    
    // Mark the pending step as approved before running
    if (approvedRunId) {
        const pendingStep = runner.report.steps.find(s => s.state === "waiting_approval");
        if (pendingStep) {
            pendingStep.approved = true;
            pendingStep.state = "running";
        }
    }
    
    runner.run().catch(e => {
        runner.updateState("failed");
        console.error(e);
        process.exit(1);
    });
}

module.exports = { WorkflowRunner };
