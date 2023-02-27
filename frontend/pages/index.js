import Head from 'next/head'
import { useEffect, useState } from 'react'
import { Typography, Container, Button, TextField, IconButton, CircularProgress, Tooltip } from '@mui/material'
import { LoadingButton } from '@mui/lab'
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import Grid from '@mui/material/Unstable_Grid2'
import Footer from '../components/Footer'

import axios from 'axios'
import moment from 'moment';

export default function Home() {
    const [rpcUrl, setRpcUrl] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState(null);

    const [currentActiveNetworks, setCurrentActiveNetworks] = useState(null);
    const [totalNetworksCreated, setTotalNetworksCreated] = useState(null);
    const [networkLifespan, setNetworkLifespan] = useState(null);
    const [maxConcurrentNetworks, setMaxConcurrentNetworks] = useState(null);

    const handleButtonClick = () => {
        if (!isLoading) {
          setError(null);
          setIsLoading(true);

          axios.post('https://sw0l2ue5r6.execute-api.eu-west-1.amazonaws.com/prod/')
          .then((response) => {
            setRpcUrl(response.data.rpc);
            setIsLoading(false);
          })
          .catch((error) => {
            try {
                setError('Error: ' + error.response.data);
            }
            catch (e) {
                setError('Error: ouch!');
            }
            setRpcUrl('');
            setIsLoading(false);
          });        
        }
    };

    useEffect(() => {
        (async () => {
            const result = await axios.get('https://sw0l2ue5r6.execute-api.eu-west-1.amazonaws.com/prod/stats');

            setCurrentActiveNetworks(result.data.currentActiveNetworks);
            setTotalNetworksCreated(result.data.totalNetworksCreated);
            setNetworkLifespan(result.data.networkLifespan);
            setMaxConcurrentNetworks(result.data.maxConcurrentNetworks);
        })()
    }, [])


    return (
        <Container style={{marginTop: '2em'}}>
            <Head>
                <title>testnet.fyi</title>
                <meta name="description" content="testnet.fyi" />
            </Head>
                <div>
                    <Container maxWidth="lg">
                        <Typography variant="h3" textAlign="center" fontWeight="700">🧪 TESTNET<span style={{fontSize: "0em"}}> </span>.FYI 🏗️</Typography>
                        {/* animated keyframes gradient text */}
                        <Grid container direction="column" spacing={1} alignItems="top" justifyContent="center">
                            <Grid item>
                            <Typography variant="h3" fontSize="2em" textAlign="center" className="linear-wipe" fontWeight="700">
                                Ethereum testnet as a service
                            </Typography>
                            </Grid>
                            <Grid item>
                            <Typography textAlign="center">
                                Create shareable short lived testnets 
                                { networkLifespan && <> ({moment.duration(networkLifespan, 'seconds').asMinutes()} mins)</>}
                            </Typography>
                            </Grid>
                            <Grid>
                                <Grid container spacing={1} justifyContent="center">
                                    <Grid item  alignItems="stretch" style={{ display: "flex" }}>
                                        <LoadingButton variant="contained" loading={isLoading} onClick={handleButtonClick}>Create</LoadingButton>
                                    </Grid>
                                    <Grid item>
                                        <TextField
                                            sx={{ width: '28ch' }}
                                            label="RPC URL"
                                            value={rpcUrl}
                                            disabled
                                            InputProps={{endAdornment: <IconButton onClick={() => {navigator.clipboard.writeText(rpcUrl)}} ><ContentCopyIcon/></IconButton>}}
                                        />
                                    </Grid>
                                </Grid>
                            </Grid>
                            {error && 
                                <Grid>
                                <Typography color='red' textAlign="center">
                                    {error}
                                </Typography>
                                </Grid>
                            }

                            {currentActiveNetworks && 
                                <Grid>
                                <Typography textAlign="center">
                                    Current active networks/max: {currentActiveNetworks}/{maxConcurrentNetworks}
                                </Typography>
                                </Grid>
                            }

                            {totalNetworksCreated && 
                                <Grid>
                                <Typography textAlign="center">
                                    Networks created since&nbsp;
                                    <Tooltip title="2023-02-24">
                                        <Typography sx={{textDecoration: 'underline'}} display="inline">
                                        launch
                                        </Typography>
                                    </Tooltip>
                                    : {totalNetworksCreated}
                                </Typography>
                                </Grid>
                            }
                        </Grid>
                    </Container>
                </div>
            <Footer/>
        </Container>
    )
}
