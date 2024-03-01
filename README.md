This [streamlit](https://streamlit.io/) app help to plot analytics value to manage the fablab.

# Deploy Streamlit using Docker
Based on the [streamlit documentation](https://docs.streamlit.io/knowledge-base/tutorials/deploy/docker).  

Build the image:
```sh
docker build -t analyticslab .
```

Run the Docker container
```sh
docker run -p 8501:8501 --env-file .env analyticslab
```
