import React, { useState, useEffect } from 'react';
import { FileText, Receipt, FileBarChart, Filter, Search, ChevronRight } from 'lucide-react';
import { listWorkflows, listWorkflowCategories } from '../services/api';

const WorkflowSelector = ({ onWorkflowSelect }) => {
  const [workflows, setWorkflows] = useState([]);
  const [filteredWorkflows, setFilteredWorkflows] = useState([]);
  const [categories, setCategories] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Icon mapping for workflows
  const iconMap = {
    'cv': FileText,
    'receipt': Receipt,
    'invoice': FileBarChart,
    'default': FileText,
  };

  useEffect(() => {
    loadWorkflows();
    loadCategories();
  }, []);

  useEffect(() => {
    filterWorkflows();
  }, [workflows, selectedCategory, searchQuery]);

  const loadWorkflows = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await listWorkflows();
      setWorkflows(data);
      setFilteredWorkflows(data);
    } catch (err) {
      console.error('Failed to load workflows:', err);
      setError('Failed to load workflows. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const loadCategories = async () => {
    try {
      const data = await listWorkflowCategories();
      setCategories(['all', ...data]);
    } catch (err) {
      console.error('Failed to load categories:', err);
    }
  };

  const filterWorkflows = () => {
    let filtered = workflows;

    // Filter by category
    if (selectedCategory !== 'all') {
      filtered = filtered.filter(wf => wf.category === selectedCategory);
    }

    // Filter by search query
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(wf =>
        wf.name.toLowerCase().includes(query) ||
        wf.description.toLowerCase().includes(query)
      );
    }

    setFilteredWorkflows(filtered);
  };

  const handleWorkflowClick = (workflow) => {
    if (onWorkflowSelect) {
      onWorkflowSelect(workflow);
    }
  };

  const getIcon = (iconName) => {
    const Icon = iconMap[iconName] || iconMap.default;
    return Icon;
  };

  if (loading) {
    return (
      <div className="card">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-gray-200 rounded w-1/3"></div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {[1, 2, 3, 4].map(i => (
              <div key={i} className="h-32 bg-gray-200 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card">
        <div className="p-4 bg-danger-50 border border-danger-200 rounded-lg">
          <p className="text-danger-800">{error}</p>
          <button
            onClick={loadWorkflows}
            className="btn btn-secondary mt-2"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="card">
      <h2 className="text-2xl font-bold mb-4 text-gray-800">Select Workflow</h2>
      <p className="text-gray-600 mb-6">
        Choose a workflow template to process your document
      </p>

      {/* Filters */}
      <div className="mb-6 space-y-4">
        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
          <input
            type="text"
            placeholder="Search workflows..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
          />
        </div>

        {/* Category Filter */}
        <div className="flex items-center space-x-2">
          <Filter className="h-5 w-5 text-gray-500" />
          <div className="flex flex-wrap gap-2">
            {categories.map(category => (
              <button
                key={category}
                onClick={() => setSelectedCategory(category)}
                className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors ${
                  selectedCategory === category
                    ? 'bg-primary-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                {category.charAt(0).toUpperCase() + category.slice(1)}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Workflow Cards */}
      {filteredWorkflows.length === 0 ? (
        <div className="text-center py-12">
          <FileText className="mx-auto h-12 w-12 text-gray-400 mb-4" />
          <p className="text-gray-600">No workflows found</p>
          <p className="text-sm text-gray-500 mt-2">
            Try adjusting your search or filters
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filteredWorkflows.map(workflow => {
            const Icon = getIcon(workflow.icon);
            return (
              <button
                key={workflow.workflow_id}
                onClick={() => handleWorkflowClick(workflow)}
                className="flex items-start p-4 border-2 border-gray-200 rounded-lg hover:border-primary-500 hover:bg-primary-50 transition-all text-left group"
              >
                <div className="flex-shrink-0 mr-4">
                  <div className="w-12 h-12 bg-primary-100 rounded-lg flex items-center justify-center group-hover:bg-primary-200 transition-colors">
                    <Icon className="h-6 w-6 text-primary-600" />
                  </div>
                </div>
                <div className="flex-grow min-w-0">
                  <div className="flex items-start justify-between mb-1">
                    <h3 className="font-semibold text-gray-900 group-hover:text-primary-700 transition-colors">
                      {workflow.name}
                    </h3>
                    <ChevronRight className="h-5 w-5 text-gray-400 group-hover:text-primary-600 flex-shrink-0 ml-2" />
                  </div>
                  <p className="text-sm text-gray-600 mb-2 line-clamp-2">
                    {workflow.description}
                  </p>
                  <div className="flex flex-wrap gap-1">
                    {workflow.document_types.slice(0, 3).map(docType => (
                      <span
                        key={docType}
                        className="px-2 py-0.5 bg-gray-100 text-gray-600 text-xs rounded"
                      >
                        {docType.toUpperCase()}
                      </span>
                    ))}
                    {workflow.document_types.length > 3 && (
                      <span className="px-2 py-0.5 bg-gray-100 text-gray-600 text-xs rounded">
                        +{workflow.document_types.length - 3}
                      </span>
                    )}
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      )}

      {/* Example Intents Section */}
      {filteredWorkflows.length > 0 && selectedCategory !== 'all' && (
        <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
          <h4 className="font-medium text-blue-900 mb-2">Example Use Cases:</h4>
          <ul className="space-y-1">
            {filteredWorkflows[0].example_intents.slice(0, 3).map((example, idx) => (
              <li key={idx} className="text-sm text-blue-800">
                • {example}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};

export default WorkflowSelector;
