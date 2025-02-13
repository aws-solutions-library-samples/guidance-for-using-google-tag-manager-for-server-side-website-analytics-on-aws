# Steps for configuring your webapp with cognito

If you are looking to implement the server side tagging on your web app that is 
    1. Written in Angular
    2. Hosted in S3
    3. Distributed using cloud front
use below configuration steps

## Update Angular server side code
### Update index.html
1. Add below under `<head>` Use the GTM Container id of the Web container 
```
  <!-- Google Tag Manager -->
  <script>(function(w,d,s,l,i){w[l]=w[l]||[];w[l].push({'gtm.start':
    new Date().getTime(),event:'gtm.js'});var f=d.getElementsByTagName(s)[0],
    j=d.createElement(s),dl=l!='dataLayer'?'&l='+l:'';j.async=true;j.src=
    'https://www.googletagmanager.com/gtm.js?id='+i+dl;f.parentNode.insertBefore(j,f);
    })(window,document,'script','dataLayer','GTM-XXXXXXXX');
  </script>
  <!-- End Google Tag Manager -->
```
2. Add below under `<body>` Use the GTM Container id of the Web container 
```
  <!-- Google Tag Manager (noscript) -->
  <noscript><iframe src="https://www.googletagmanager.com/ns.html?id=GTM-XXXXXXXX"
  height="0" width="0" style="display:none;visibility:hidden"></iframe></noscript>
  <!-- End Google Tag Manager (noscript) -->
```
## Update cloudfront distribution with domain name and ACM certificate
1. Open cloudfront console and navigate to the cloudfront distribution of the webapp
2. Edit General -> Settings and add the root DNS domain of the webapp and attach the custom SSL certificate that includes the root, the server side tagging url and the login url's
## Update cognito configurations
1. In the the SSL certificate make sure you have an entry for the URL that will be used for cognito login page. For example "login.example.com"
2. Navigate to cognito console, open the userpool. Then navigate to the application client that is configured for your web applicaiton
3. Open the login pages tag and add the the home page of the webapp as the "Allowed call back URLs". Set "Allowed sign-out URLs" as required
4. Navigate to Branding -> Managed login and create a new style and select the web app client

