import type {SidebarsConfig} from '@docusaurus/plugin-content-docs';

const sidebars: SidebarsConfig = {
  tutorialSidebar: [
    'intro',
    'getting-started',
    {
      type: 'category',
      label: 'Architecture',
      items: [
        'architecture/overview',
        'architecture/data-flow',
        'architecture/tech-stack',
      ],
    },
    {
      type: 'category',
      label: 'Backend',
      items: [
        'backend/overview',
        'backend/api-routes',
        'backend/database',
        'backend/services',
        'backend/auth',
        'backend/config',
      ],
    },
    {
      type: 'category',
      label: 'Frontend',
      items: [
        'frontend/overview',
        'frontend/components',
        'frontend/routing',
        'frontend/i18n',
        'frontend/styling',
      ],
    },
    {
      type: 'category',
      label: 'Worker',
      items: [
        'worker/overview',
        'worker/data-pipeline',
        'worker/ibkr-flex',
        'worker/scheduler',
      ],
    },
    {
      type: 'category',
      label: 'AI Agents',
      items: [
        'agents/overview',
        'agents/architecture',
        'agents/copilot',
        'agents/trade-decision',
        'agents/trade-review',
        'agents/daily-review',
        'agents/risk-assessment',
        'agents/structured-output',
        'agents/eval-harness',
      ],
    },
    {
      type: 'category',
      label: 'Deployment',
      items: [
        'deployment/local',
        'deployment/docker',
        'deployment/production',
      ],
    },
    {
      type: 'category',
      label: 'API Reference',
      items: [
        'api/overview',
        'api/auth',
        'api/account',
        'api/positions',
        'api/trades',
        'api/charts',
        'api/copilot',
        'api/agents',
        'api/mcp',
        'api/admin',
      ],
    },
    {
      type: 'category',
      label: 'Development',
      items: [
        'dev/contributing',
        'dev/testing',
        'dev/debugging',
      ],
    },
  ],
};

export default sidebars;
