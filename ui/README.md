# Prompt Tester Streamlit Interface

A systematic web interface for analyzing experimental prompt optimization results through side-by-side comparison and data-driven insights.

## 🚀 Quick Start

### Prerequisites
- Existing experimental data from the Prompt Tester CLI tool
- Python virtual environment with dependencies installed

### Launch the Interface

From the project root directory:

```bash
# Activate virtual environment
source venv/bin/activate

# Launch Streamlit interface
streamlit run ui/streamlit_app.py
```

The interface will open in your default browser, typically at `http://localhost:8501`

## 🔧 Features

### Phase 1 Implementation (Current)

#### 📊 Results Summary
- **Run Selection**: Choose from available experimental runs with success rates
- **Key Metrics**: View success rates, response lengths, and experiment counts  
- **Status Distribution**: Visualize experiment success/failure patterns
- **Recent Results**: Quick access to latest experimental data

#### ⚖️ Side-by-Side Comparison
- **Multi-Prompt Comparison**: Compare 2-3 prompts simultaneously
- **Test Case Focus**: Deep-dive into specific test case responses
- **Response Analysis**: View full responses with metadata
- **Visual Status Indicators**: Clear success/failure feedback

#### 🔍 Advanced Filtering
- **Prompt Selection**: Choose which prompts to analyze
- **Test Case Filtering**: Focus on specific scenarios
- **Model Filtering**: Filter by AI model used
- **Status Filtering**: Show only successful experiments
- **Text Search**: Search within responses and prompts

#### 📊 Data Explorer
- **Raw Data Access**: Full database exploration
- **Column Selection**: Choose which fields to display
- **Sorting & Filtering**: Custom data organization
- **Export Functionality**: Download filtered results

## 💡 Usage Workflows

### Workflow 1: Compare Prompt Performance
1. **Select Run**: Choose an experimental run from the sidebar
2. **Filter Prompts**: Select 2-3 prompts for comparison
3. **Navigate to Comparison Tab**: View side-by-side results
4. **Analyze Responses**: Compare quality, length, and accuracy

### Workflow 2: Analyze Experiment Results
1. **Choose Recent Run**: Select from completed experiments
2. **Review Summary**: Check overall success rates and metrics
3. **Filter by Status**: Focus on successful results
4. **Export Data**: Download results for further analysis

### Workflow 3: Deep Dive Analysis
1. **Use Data Explorer**: Access raw experimental data
2. **Apply Custom Filters**: Narrow down to specific scenarios
3. **Search Content**: Find relevant responses using text search
4. **Export Findings**: Save filtered data for documentation

## 🎯 Key Interface Elements

### Sidebar Controls
- **Run Selector**: Dropdown with run timestamps and success rates
- **Filter Panel**: Multi-select widgets for data filtering
- **Search Box**: Text search across responses
- **Clear Filters**: Reset all applied filters

### Main Content Tabs
- **Results Summary**: High-level metrics and visualizations
- **Side-by-Side Comparison**: Detailed prompt comparison interface  
- **Data Explorer**: Raw data access with export functionality

## 📈 Performance Features

- **Caching**: Database queries cached for 60 seconds
- **Responsive Design**: Adapts to different screen sizes
- **Error Handling**: Graceful handling of missing data
- **Real-time Filtering**: Instant updates when changing filters

## 🔗 Architecture Integration

- **Zero Changes**: Preserves existing CLI and storage architecture
- **Direct Database Access**: Uses existing SQLite database via read-only connections
- **Modular Design**: Components can be extended for future features
- **Data Integrity**: Maintains experimental data as invariant manifolds

## 📝 Next Steps (Future Phases)

### Phase 2: UX Improvements
- Enhanced text search with highlighting
- Better markdown rendering in responses
- Improved loading states and error messages
- Performance optimizations for large datasets

### Phase 3: Blind Testing Interface
- Anonymous A/B testing interface
- Session-based preference tracking
- Comparative evaluation workflows
- Statistical significance analysis

## ⚠️ Notes

- Requires experimental data from CLI runs
- Interface is read-only (no data modification)
- Optimized for typical experimental dataset sizes
- Uses session state for temporary UI preferences

## 🐛 Troubleshooting

### Common Issues

**"No experimental runs found"**
- Run experiments using the CLI tool first
- Ensure `results.db` exists in project root

**"Database error"**
- Check that `results.db` is readable
- Verify no other processes are locking the database

**Import errors**
- Ensure all dependencies are installed: `pip install streamlit pandas`
- Verify virtual environment is activated

**Empty results**
- Check applied filters - try clearing all filters
- Verify selected run contains data

---

*Built with mathematical precision and algorithmic elegance for optimal prompt analysis workflows.*
