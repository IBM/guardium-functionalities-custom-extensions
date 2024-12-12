const axios = require('axios');
const https = require('https');

// Read sensitive data from environment variables
const client_id = process.env.CLIENT_ID;
const client_secret = process.env.CLIENT_SECRET;
const redirect_uri = process.env.REDIRECT_URI;
const oauth_url = process.env.OAUTH_URL;
const create_update_user_url = process.env.CREATE_USER;
const list_reports_url = process.env.LIST_REPORTS_URL;
const datasource_group_url = process.env.DATASOURCE_GROUP_URL;
const stapHost_all_active_url = process.env.STAPHOST_ALL_ACTIVE_URL;
const list_installed_policies_url = process.env.LIST_INSTALLED_POLICIES_URL;
const policy_url = process.env.POLICY_URL;


// Create an HTTPS agent that ignores self-signed certificates
const agent = new https.Agent({
  rejectUnauthorized: false,
});

// Function to obtain token
async function obtainToken(username, password) {
  try {
    const response = await axios.post(
      oauth_url,
      new URLSearchParams({
        client_id,
        client_secret,
        grant_type: 'password',
        username,
        password,
        redirect_uri,
      }),
      {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        httpsAgent: agent,
      }
    );
    return response.data.access_token;
  } catch (error) {
    console.error('Error obtaining token:', error);
    throw error;
  }
}

// Function to create or update user
async function manageUser(params, token, type) {
  const headers = {
    Authorization: `Bearer ${token}`,
    'Content-Type': 'application/json',
  };

  const createParams = {
    firstName: params.firstName,
    lastName: params.lastName,
    password: params.password,
    confirmPassword: params.confirmPassword,
    userName: params.userName,
    disabled: params.disabled,
  }

  const updateParams = {
    userName: params.userName,
    disabled: params.disabled,
  }

  const url = create_update_user_url;
  const method = type === 'createUser' ? 'post' : 'put';
  const bodyObj = type === 'createUser' ? createParams : updateParams;

  

  try {
    const response = await axios[method](
      url,
      bodyObj,
      { headers, httpsAgent: agent }
    );
    return {
      statusCode: response.status,
      body: JSON.stringify({
        message: response.status === 200 ? `${type} succeeded.` : `${type} failed.`,
        user: response.data,
      }),
    };
  } catch (error) {
    console.error(`Error in ${type}:`, error);
    throw error;
  }
}

// Function to list reports
async function listReports(token, searchKey) {
  try {
    const response = await axios.get(list_reports_url, {
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      httpsAgent: agent,
    });

    const listArray = response.data.data;
    const filteredList = listArray.filter((li) =>
      li.toLowerCase().includes(searchKey.toLowerCase())
    );
    return filteredList;
  } catch (error) {
    console.error('Error listing reports:', error);
    throw error;
  }
}


// Main function to handle various types of operations
async function main(params) {
  const { type, loggedUserName, loggedUserPassword } = params;

  try {
    const token = await obtainToken(loggedUserName, loggedUserPassword);

    if (type === 'createUser' || type === 'updateUser') {
      return await manageUser(params, token, type);
    } else if (type === 'listAllReport') {
      const searchKey = params.searchKey || '';
      const reportList = await listReports(token, searchKey);
      return { statusCode: 200, body: JSON.stringify(reportList, null, 2) };
    } else if (type === 'datasourceGroup') {
      const response = await axios.get(datasource_group_url, {
        headers: { Authorization: `Bearer ${token}` },
        httpsAgent: agent,
      });
      return { statusCode: 200, body: JSON.stringify(response.data, null, 2) };
    } else if (type === 'stapHostAllActive') {
      const response = await axios.get(stapHost_all_active_url, {
        headers: { Authorization: `Bearer ${token}` },
        httpsAgent: agent,
      });
      return { statusCode: 200, body: JSON.stringify(response.data, null, 2) };
    } else if (type === 'installedPolicies') {
      const response = await axios.get(list_installed_policies_url, {
        headers: { Authorization: `Bearer ${token}` },
        httpsAgent: agent,
      });
      const res = JSON.parse(response.data.Message).split(':[')[2].split(',');
      res[res.length - 1] = res[res.length - 1].split(']]')[0];
      return { statusCode: 200, body: JSON.stringify(res, null, 2) };
    } else if (type === 'policy') {
      const response = await axios.get(policy_url, {
        headers: { Authorization: `Bearer ${token}` },
        httpsAgent: agent,
      });
      return { statusCode: 200, body: JSON.stringify(response.data, null, 2) };
    } else {
      return { statusCode: 400, body: JSON.stringify({ error: 'Invalid type parameter' }) };
    }
  } catch (error) {
    console.error('Error:', error);
    return {
      statusCode: error.response ? error.response.status : 500,
      body: JSON.stringify({ error: error.message }),
    };
  }
}

// Example of dynamically calling the main function
const inputParams = {
  type: 'updateUser',
  reportName: 'Policy Violations',
  fromDate: '2024-08-13 00:00:00',
  toDate: '2024-08-14 00:00:00',
  searchKey: 'MS-SQL',
  userName: 'username',
  password: 'password',
  confirmPassword: 'password',
  firstName: 'HUser',
  lastName: 'GUser',
  disabled: 1,
  loggedUserName: 'loggedUserName',
  loggedUserPassword: 'loggedUserPassword'
};

main(inputParams)
  .then((result) => {
    console.log('Result:', result);
  })
  .catch(console.error);

module.exports = { main };
