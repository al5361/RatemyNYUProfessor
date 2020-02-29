Read me:
1.    To run the back end code to fetch data from the Stern CFE database, you need to be logged into the database. To update the SQL database when new CFE scores are released, log into Stern CFE and obtain the curl link, convert it to python code, and replace the current code in the backend file.
2.    Modifications to the SQL database done in SQL and not included in this .zip file:
a.    Deleted all entries with 0 as number of responses
b.    Modified datatypes of the columns
3.    Outliers: courses “Business and It’s Publics” and “Professional Leadership” have their own scale on the Stern CFE database. These entries are excluded from all aggregate analysis and professor based analysis for consistency purposes. However, they are kept in the SQL database so that analysis could be done on these two courses in an isolated way, for course based analysis.
4.    The images of professors and plots in the static folder are not necessary for the webpage to function. They are generated by visits to the webpage. We kept them in the static folder for simplicity purposes. 4 images in the static folder labeled with “ _home” at the end are necessary for the front page to display professor images of our choice.
5.    Notebooks: Analytics Notes 1 & 2 are messy notes, drafts, and tests. Most functioning parts of the code there are used in the “frontend.py” file for the final product.
