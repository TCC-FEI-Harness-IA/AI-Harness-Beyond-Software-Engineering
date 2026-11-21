/* eslint-env node */

// Restringe `import.meta.env` a src/config/env.ts (regra 4 do README).
const NO_IMPORT_META_ENV = {
  selector: "MemberExpression[object.type='MetaProperty'][property.name='env']",
  message: 'import.meta.env só pode ser lido em src/config/env.ts.',
}

// Restringe `window.location.reload()` (regra 8 do README — sem refresh).
const NO_LOCATION_RELOAD = {
  selector:
    "CallExpression[callee.object.object.name='window'][callee.object.property.name='location'][callee.property.name='reload']",
  message: 'Não use window.location.reload(); a navegação é feita pelo estado do React.',
}

module.exports = {
  root: true,
  env: { browser: true, es2022: true, node: true },
  extends: ['eslint:recommended'],
  ignorePatterns: ['dist'],
  overrides: [
    {
      files: ['src/**/*.{ts,tsx}'],
      parser: '@typescript-eslint/parser',
      parserOptions: {
        ecmaVersion: 'latest',
        sourceType: 'module',
        project: './tsconfig.json',
      },
      plugins: ['@typescript-eslint', 'react-hooks', 'react-refresh'],
      extends: ['plugin:@typescript-eslint/recommended', 'plugin:react-hooks/recommended'],
      rules: {
        '@typescript-eslint/no-explicit-any': 'error',
        '@typescript-eslint/no-floating-promises': 'error',
        '@typescript-eslint/consistent-type-imports': 'error',
        '@typescript-eslint/no-unused-vars': [
          'error',
          { argsIgnorePattern: '^_', varsIgnorePattern: '^_' },
        ],
        'react-hooks/rules-of-hooks': 'error',
        'react-hooks/exhaustive-deps': 'error',
        'no-restricted-syntax': ['error', NO_IMPORT_META_ENV, NO_LOCATION_RELOAD],
        'no-restricted-globals': [
          'error',
          { name: 'fetch', message: 'fetch só pode ser usado em src/api/**.' },
        ],
      },
    },
    {
      files: ['src/config/env.ts'],
      rules: {
        'no-restricted-syntax': 'off',
      },
    },
    {
      files: ['src/api/**/*.{ts,tsx}'],
      rules: {
        'no-restricted-globals': 'off',
      },
    },
    {
      files: ['vite.config.ts'],
      parser: '@typescript-eslint/parser',
      parserOptions: {
        ecmaVersion: 'latest',
        sourceType: 'module',
        project: './tsconfig.node.json',
      },
      plugins: ['@typescript-eslint'],
      extends: ['plugin:@typescript-eslint/recommended'],
    },
  ],
}
