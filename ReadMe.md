#### Create Virtual environment
``` 
python3 -m venv env 
```

#### Activate virtual environment
```
source env/bin/activate
```

#### Install Requirements
```
pip install -r requirements.txt
```

#### Run Streamlit app
```
streamlit run pg_sql_agent_gpt_model.py
```

> Add postgres DB details and open API ssh key in .env
>
> To generate the Open API key [URL](https://platform.openai.com/settings/organization/api-keys)