#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { NetworkStack } from '../lib/stacks/network-stack';
import { CognitoStack } from '../lib/stacks/cognito-stack';
import { CertificateStack } from '../lib/stacks/certificate-stack';
import { SecretsStack } from '../lib/stacks/secrets-stack';
import { DatabaseStack } from '../lib/stacks/database-stack';
import { ApplicationStack } from '../lib/stacks/application-stack';
import { getEnvironmentConfig } from '../lib/config/environments';

const app = new cdk.App();

// Get environment from context or default to 'dev'
const envName = app.node.tryGetContext('env') || 'dev';
const config = getEnvironmentConfig(envName);

// Validate required configuration
if (!config.account) {
  console.warn('Warning: CDK_DEFAULT_ACCOUNT not set. Using current AWS account.');
}

const env: cdk.Environment = {
  account: config.account || process.env.CDK_DEFAULT_ACCOUNT,
  region: config.region,
};

// Common tags for all resources
const tags = {
  Project: 'Mantrix-Axis-AI',
  Environment: config.envName,
  ManagedBy: 'CDK',
};

// Stack naming convention
const stackPrefix = `Mantrix-${config.envName}`;

/**
 * Stack 1: Network Infrastructure
 * VPC, Subnets, NAT Instance/Gateway, Security Groups
 */
const networkStack = new NetworkStack(app, `${stackPrefix}-Network`, {
  env,
  config,
  description: 'Mantrix Axis AI - Network infrastructure (VPC, subnets, security groups)',
  tags,
});

/**
 * Stack 2: Authentication
 * Cognito User Pool, Client, Groups
 */
const cognitoStack = new CognitoStack(app, `${stackPrefix}-Cognito`, {
  env,
  config,
  description: 'Mantrix Axis AI - Authentication (Cognito User Pool)',
  tags,
});

/**
 * Stack 3: SSL/TLS Certificate
 * ACM Certificate with Route 53 DNS validation
 */
const certificateStack = new CertificateStack(app, `${stackPrefix}-Certificate`, {
  env,
  config,
  description: 'Mantrix Axis AI - SSL Certificate (ACM)',
  tags,
});

/**
 * Stack 4: Secrets Management
 * AWS Secrets Manager for API keys and credentials
 */
const secretsStack = new SecretsStack(app, `${stackPrefix}-Secrets`, {
  env,
  config,
  description: 'Mantrix Axis AI - Secrets Management',
  tags,
});

/**
 * Stack 5: Databases
 * RDS PostgreSQL, ElastiCache Redis, EFS for MongoDB/Weaviate
 */
const databaseStack = new DatabaseStack(app, `${stackPrefix}-Database`, {
  env,
  config,
  vpc: networkStack.vpc,
  databaseSecurityGroup: networkStack.databaseSecurityGroup,
  description: 'Mantrix Axis AI - Databases (RDS, ElastiCache, EFS)',
  tags,
});
databaseStack.addDependency(networkStack);

/**
 * Stack 6: Application
 * ECS Cluster, Fargate Services, ALB
 */
const applicationStack = new ApplicationStack(app, `${stackPrefix}-Application`, {
  env,
  config,
  vpc: networkStack.vpc,
  backendSecurityGroup: networkStack.backendSecurityGroup,
  frontendSecurityGroup: networkStack.frontendSecurityGroup,
  dataServicesSecurityGroup: networkStack.dataServicesSecurityGroup,
  albSecurityGroup: networkStack.albSecurityGroup,
  certificate: certificateStack.certificate,
  hostedZone: certificateStack.hostedZone,
  userPool: cognitoStack.userPool,
  userPoolClient: cognitoStack.userPoolClient,
  secrets: secretsStack,
  rdsInstance: databaseStack.rdsInstance,
  rdsSecret: databaseStack.rdsSecret,
  redisCluster: databaseStack.redisCluster,
  efsFileSystem: databaseStack.efsFileSystem,
  description: 'Mantrix Axis AI - Application (ECS, ALB)',
  tags,
});
applicationStack.addDependency(networkStack);
applicationStack.addDependency(cognitoStack);
applicationStack.addDependency(certificateStack);
applicationStack.addDependency(secretsStack);
applicationStack.addDependency(databaseStack);

app.synth();
