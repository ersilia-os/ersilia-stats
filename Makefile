run_app:
	python3 -m dashboard.app & sleep 30

	wget -r http://127.0.0.1:8050/
	wget -r http://127.0.0.1:8050/_dash-layout 
	wget -r http://127.0.0.1:8050/_dash-dependencies

	wget -r http://127.0.0.1:8050/_dash-component-suites/dash/dcc/async-graph.js
	wget -r http://127.0.0.1:8050/_dash-component-suites/dash/dcc/async-highlight.js
	wget -r http://127.0.0.1:8050/_dash-component-suites/dash/dcc/async-markdown.js
	wget -r http://127.0.0.1:8050/_dash-component-suites/dash/dcc/async-datepicker.js

	wget -r http://127.0.0.1:8050/_dash-component-suites/dash/dash_table/async-table.js
	wget -r http://127.0.0.1:8050/_dash-component-suites/dash/dash_table/async-highlight.js

	wget -r http://127.0.0.1:8050/_dash-component-suites/plotly/package_data/plotly.min.js

	wget -r http://127.0.0.1:8050/dashboard/assets/style.css
	wget -r http://127.0.0.1:8050/dashboard/assets/custom.js
	ls 127.0.0.1:8050/dashboard/assets

	mv 127.0.0.1:8050/dashboard pages_files
	mv 127.0.0.1:8050/dashboard/assets pages_files/assets
	ls -a pages_files
	if [ ! -d "pages_files/dashboard/assets" ]; then echo "Assets directory missing"; exit 1; fi
	ls -a pages_files/assets
	
	REPO_PATH=ersilia-os/ersilia-stats

	find pages_files -type f -exec sed -i.bak "s|_dash-component-suites|${REPO_PATH}/_dash-component-suites|g" {} \;
	find pages_files -type f -exec sed -i.bak "s|_dash-layout|${REPO_PATH}/_dash-layout.json|g" {} \;
	find pages_files -type f -exec sed -i.bak "s|_dash-dependencies|${REPO_PATH}/_dash-dependencies.json|g" {} \;
	find pages_files -type f -exec sed -i.bak "s|_reload-hash|${REPO_PATH}/_reload-hash|g" {} \;
	find pages_files -type f -exec sed -i.bak "s|_dash-update-component|${REPO_PATH}/_dash-update-component|g" {} \;
	find pages_files -type f -exec sed -i.bak "s|assets|${REPO_PATH}/dashboard/assets|g" {} \;


	mv pages_files/_dash-layout pages_files/_dash-layout.json
	mv pages_files/_dash-dependencies pages_files/_dash-dependencies.json

	ps -C python -o pid= | xargs -r kill -9

clean_dirs:
	ls
	rm -rf 127.0.0.1:8050/
	rm -rf pages_files/
	rm -rf joblib
