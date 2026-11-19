# **DAEN 328 Term Project — Phase 1 Report**

# **1\. Team**

**Team Number: 7**  
**Group Leader: Hunter Cruce**

* **Yohan Arul \- yohanarul@tamu.edu**  
* **Ethan Rasmussen \- ethan.rasmussen@tamu.edu**   
* **Navya Vegesna \- nvv2006@tamu.edu**  
* **Hunter Cruce \- huntercruce@tamu.edu** 

## **Team GitHub Repository Link** 

[https\://github.com/HunterC42/term\_project.git](https://github.com/HunterC42/term_project.git) 

# **2\. Data Source**

## **Primary Dataset Overview**

Our team selected the Chicago Crimes Dataset from the dataset options provided on canvas. This dataset contains information about reported crimes in Chicago, including the date, type of crime, and location.   
 

* **Dataset Name**: Chicago Crimes  
* **Source**: Options File  
* **JSON URL**: [https\://data.cityofchicago.org/resource/ijzp-q8t2.json](https://data.cityofchicago.org/resource/ijzp-q8t2.json)   
* **Dataset URL**: [https\://data.cityofchicago.org/Public-Safety/Crimes-2001-to-Present/ijzp-q8t2/data\_preview](https://data.cityofchicago.org/Public-Safety/Crimes-2001-to-Present/ijzp-q8t2/data_preview)  
* **API Key**: The API is publicly accessible and does not require an API key for basic requests.  
* **Incremental Pulls**: We plan to use the updated\_on column to identify crime records that have been added or modified since the last successful data pull. We will also use the id column to identify each crime record and prevent duplicates when loading the data into PostgreSQL.

# **3\. Proof it Works**

We tested the Chicago Crimes API and successfully retrieved crime records. We loaded the data into a pandas DataFrame containing 31 columns, confirming that the API works and the data can be accessed for our project.

# **4\. Data Description**

**Dataset Size:**​​ The Chicago Crimes Dataset contains millions of crime records from 2001\. In our initial API test, we retrieved 1,000 rows and 31 columns. We plan to work with a subset of data for our project to make processing more manageable.  

**Questions:**

1. Which areas of Chicago have the most reported crimes?  
2. Is there a correlation between types of crime and regions in the city?  
3. Is crime density per region proportional to population density?  
4. How have crime patterns changed over time in different regions of Chicago?  
5. What are the most common types of crime reported in Chicago?

| Column Name | Type |
| :---- | :---- |
| case\_number | String (VARCHAR) |
| primary\_type | String (VARCHAR) |
| arrest | Bool |

**Source Update Frequency:** Daily

**Database Tables Expected:**  
**Crimes:** Stores individual crime records, including crime ID, date, crime type, location, community\_area, and arrest status. Primary Key: id.

**Community\_Areas:** Stores information about Chicago’s community areas, including the population and area size from a different dataset. Primary Key: community\_area.

**Table Relationship:** The Crimes table connects to the Community\_Areas table using the community\_area column as a foreign key. The relationship allows us to compare crime patterns across different areas of Chicago and look at the relationship between crime density and population. 

# **5\. Plan and Roles**

**Plan and roles:**

Yohan: Extract (API)  
Ethan: Transform (data cleaning)  
Hunter: Dashboard   
Navya: Load (PostgreSQL) and Docker

**Potential Risk**: One risk we might face is the large size of the dataset, which would slow down data processing and loading into PostgreSQL.

**How we will handle it**: We plan to retrieve the data in smaller batches and work with a subset of data to make processing more manageable. We will also test our pipeline with smaller amounts of data before processing larger datasets. 