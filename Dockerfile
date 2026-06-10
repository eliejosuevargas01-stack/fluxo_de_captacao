FROM nginx:alpine

# Copy the main index.html to Nginx html directory
COPY index.html /usr/share/nginx/html/



# Custom Nginx configuration: redirect "/" to "/index.html"
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose HTTP port
EXPOSE 80
