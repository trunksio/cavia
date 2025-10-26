import React, { useState, useEffect } from 'react';
import { AlertCircle, CheckCircle, ChevronLeft, FileText, Settings, Target, Shield } from 'lucide-react';
import { createIntentFromTemplate } from '../services/api';

const IntentCapture = ({ workflow, onIntentCreated, onBack }) => {
  const [parameters, setParameters] = useState({});
  const [intent, setIntent] = useState(null);
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);
  const [showPreview, setShowPreview] = useState(false);

  useEffect(() => {
    // Initialize parameters from workflow template
    if (workflow && workflow.intent_template) {
      const initialParams = {};
      const template = workflow.intent_template;

      // Extract placeholders from goal
      const placeholderRegex = /\{\{(\w+)\}\}/g;
      const matches = template.goal.matchAll(placeholderRegex);
      for (const match of matches) {
        const key = match[1];
        initialParams[key] = '';
      }

      // Add context parameters
      if (template.context) {
        Object.keys(template.context).forEach(key => {
          if (typeof template.context[key] === 'string') {
            initialParams[key] = template.context[key];
          }
        });
      }

      // Add constraint values
      if (template.constraints) {
        template.constraints.forEach(constraint => {
          const key = constraint.name;
          if (!initialParams[key]) {
            initialParams[key] = constraint.value || '';
          }
        });
      }

      setParameters(initialParams);
    }
  }, [workflow]);

  const handleParameterChange = (key, value) => {
    setParameters(prev => ({
      ...prev,
      [key]: value
    }));
    // Clear error for this field
    if (errors[key]) {
      setErrors(prev => {
        const newErrors = { ...prev };
        delete newErrors[key];
        return newErrors;
      });
    }
  };

  const validateParameters = () => {
    const newErrors = {};
    const template = workflow.intent_template;

    // Check required placeholders
    const placeholderRegex = /\{\{(\w+)\}\}/g;
    const matches = template.goal.matchAll(placeholderRegex);
    for (const match of matches) {
      const key = match[1];
      if (!parameters[key] || parameters[key].trim() === '') {
        newErrors[key] = `${key} is required`;
      }
    }

    // Check required constraints
    if (template.constraints) {
      template.constraints.forEach(constraint => {
        if (constraint.required) {
          const key = constraint.name;
          const value = parameters[key];
          if (value === undefined || value === null || value === '') {
            newErrors[key] = `${constraint.name} is required`;
          }
        }
      });
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleCreateIntent = async () => {
    if (!validateParameters()) {
      return;
    }

    setLoading(true);
    try {
      const createdIntent = await createIntentFromTemplate(
        workflow.workflow_id,
        parameters
      );
      setIntent(createdIntent);
      setShowPreview(true);
    } catch (err) {
      console.error('Failed to create intent:', err);
      setErrors({ _general: 'Failed to create intent. Please try again.' });
    } finally {
      setLoading(false);
    }
  };

  const handleConfirm = () => {
    if (onIntentCreated && intent) {
      onIntentCreated(intent);
    }
  };

  const renderParameterInput = (key) => {
    const value = parameters[key];
    const error = errors[key];
    const constraint = workflow.intent_template.constraints?.find(c => c.name === key);

    // Determine input type based on value type or constraint
    let inputType = 'text';
    let isArray = false;

    if (constraint) {
      if (Array.isArray(constraint.value)) {
        isArray = true;
      } else if (typeof constraint.value === 'number') {
        inputType = 'number';
      }
    }

    return (
      <div key={key} className="space-y-2">
        <label className="block text-sm font-medium text-gray-700">
          {key.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ')}
          {constraint?.required && <span className="text-danger-600 ml-1">*</span>}
        </label>

        {constraint?.description && (
          <p className="text-xs text-gray-500">{constraint.description}</p>
        )}

        {isArray ? (
          <input
            type="text"
            value={Array.isArray(value) ? value.join(', ') : value}
            onChange={(e) => handleParameterChange(key, e.target.value.split(',').map(s => s.trim()))}
            placeholder="Enter comma-separated values"
            className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent ${
              error ? 'border-danger-500' : 'border-gray-300'
            }`}
          />
        ) : (
          <input
            type={inputType}
            value={value || ''}
            onChange={(e) => handleParameterChange(key, inputType === 'number' ? Number(e.target.value) : e.target.value)}
            className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent ${
              error ? 'border-danger-500' : 'border-gray-300'
            }`}
          />
        )}

        {error && (
          <p className="text-sm text-danger-600 flex items-center">
            <AlertCircle className="h-4 w-4 mr-1" />
            {error}
          </p>
        )}
      </div>
    );
  };

  if (!workflow) {
    return null;
  }

  if (showPreview && intent) {
    return (
      <div className="card">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold text-gray-800">Intent Preview</h2>
          <button
            onClick={() => setShowPreview(false)}
            className="btn btn-secondary"
          >
            Edit
          </button>
        </div>

        <div className="space-y-6">
          {/* Goal */}
          <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <div className="flex items-start space-x-3">
              <Target className="h-5 w-5 text-blue-600 flex-shrink-0 mt-0.5" />
              <div>
                <h3 className="font-semibold text-blue-900 mb-1">Goal</h3>
                <p className="text-blue-800">{intent.goal}</p>
              </div>
            </div>
          </div>

          {/* Context */}
          {Object.keys(intent.context).length > 0 && (
            <div className="p-4 bg-gray-50 border border-gray-200 rounded-lg">
              <div className="flex items-start space-x-3">
                <Settings className="h-5 w-5 text-gray-600 flex-shrink-0 mt-0.5" />
                <div className="flex-grow">
                  <h3 className="font-semibold text-gray-900 mb-2">Context</h3>
                  <dl className="grid grid-cols-2 gap-2">
                    {Object.entries(intent.context).map(([key, value]) => (
                      <div key={key}>
                        <dt className="text-sm text-gray-600">{key}:</dt>
                        <dd className="text-sm font-medium text-gray-900">
                          {Array.isArray(value) ? value.join(', ') : String(value)}
                        </dd>
                      </div>
                    ))}
                  </dl>
                </div>
              </div>
            </div>
          )}

          {/* Constraints */}
          {intent.constraints && intent.constraints.length > 0 && (
            <div className="p-4 bg-orange-50 border border-orange-200 rounded-lg">
              <div className="flex items-start space-x-3">
                <Shield className="h-5 w-5 text-orange-600 flex-shrink-0 mt-0.5" />
                <div className="flex-grow">
                  <h3 className="font-semibold text-orange-900 mb-2">Constraints</h3>
                  <ul className="space-y-1">
                    {intent.constraints.map((constraint, idx) => (
                      <li key={idx} className="text-sm text-orange-800">
                        • {constraint.description || constraint.name}: {JSON.stringify(constraint.value)}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          )}

          {/* Success Criteria */}
          {intent.success_criteria && intent.success_criteria.length > 0 && (
            <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
              <div className="flex items-start space-x-3">
                <CheckCircle className="h-5 w-5 text-green-600 flex-shrink-0 mt-0.5" />
                <div className="flex-grow">
                  <h3 className="font-semibold text-green-900 mb-2">Success Criteria</h3>
                  <ul className="space-y-1">
                    {intent.success_criteria.map((criterion, idx) => (
                      <li key={idx} className="text-sm text-green-800">
                        • {criterion.description || criterion.criterion}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="flex space-x-3 mt-6">
          <button
            onClick={onBack}
            className="btn btn-secondary flex-1"
          >
            <ChevronLeft className="h-4 w-4 mr-2" />
            Back to Workflows
          </button>
          <button
            onClick={handleConfirm}
            className="btn btn-primary flex-1"
          >
            Continue with This Intent
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="card">
      <div className="flex items-center space-x-2 mb-6">
        <button
          onClick={onBack}
          className="text-gray-600 hover:text-gray-900"
        >
          <ChevronLeft className="h-5 w-5" />
        </button>
        <div>
          <h2 className="text-2xl font-bold text-gray-800">{workflow.name}</h2>
          <p className="text-sm text-gray-600">{workflow.description}</p>
        </div>
      </div>

      {errors._general && (
        <div className="mb-4 p-4 bg-danger-50 border border-danger-200 rounded-lg flex items-start space-x-3">
          <AlertCircle className="h-5 w-5 text-danger-600 flex-shrink-0 mt-0.5" />
          <p className="text-sm text-danger-800">{errors._general}</p>
        </div>
      )}

      <div className="space-y-6">
        <div>
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Configure Intent Parameters</h3>
          <div className="space-y-4">
            {Object.keys(parameters).map(key => renderParameterInput(key))}
          </div>
        </div>

        {workflow.example_intents && workflow.example_intents.length > 0 && (
          <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <h4 className="font-medium text-blue-900 mb-2">Example Intents:</h4>
            <ul className="space-y-1">
              {workflow.example_intents.slice(0, 3).map((example, idx) => (
                <li key={idx} className="text-sm text-blue-800">• {example}</li>
              ))}
            </ul>
          </div>
        )}
      </div>

      <div className="flex space-x-3 mt-6">
        <button
          onClick={onBack}
          className="btn btn-secondary flex-1"
        >
          <ChevronLeft className="h-4 w-4 mr-2" />
          Back
        </button>
        <button
          onClick={handleCreateIntent}
          disabled={loading}
          className="btn btn-primary flex-1"
        >
          {loading ? 'Creating Intent...' : 'Create Intent'}
        </button>
      </div>
    </div>
  );
};

export default IntentCapture;
